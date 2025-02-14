# ollama_proxy.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Middleware ##################################################################

# Can NOT run in Ipython Environment!


#####
# Ollama has NOT been tested in this version
#
# We DO NOT guarantee that this can be used in this version
#
# DONT RUN!!! MUST BE BUGS!!
#
#####

## Auto Des ###################################################################
"""
A production-grade middleware server that accepts OpenAI-style requests from a client
and forwards them to an Ollama backend. This implementation supports multiple endpoints,
including model listing, model retrieval, chat completions, text completions, edits,
and image generations. The middleware translates the incoming payload into a format
suitable for Ollama and converts its responses back into an OpenAI-style response.
"""
## Auto Des ###################################################################

import os
import json
import time
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field, ValidationError

import debug
import argsettings
import params  # custom parameters module
import socks   # custom socket module
import chatloop # NathUI chat backend

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Ollama-Middleware")

# Configuration class that holds backend and server parameters.
class Config:
    # Ollama backend URL
    OLLAMA_BACKEND_URL = params.nathui_backend_url
    
    # Port on which the middleware server will listen.
    MIDDLEWARE_PORT = socks.next_port(params.nathui_backend_middleware_starting_port)
   
    # Request timeout in seconds.
    REQUEST_TIMEOUT = 6000

def convert_chat_to_prompt(messages: list) -> str:
    """
    Convert OpenAI chat messages into a single prompt string suitable for Ollama.
    Each message is prefixed by its role and appended with a newline.
    The prompt ends with "Assistant:" to signal that a response is expected.
    """
    prompt_lines = []
    for message in messages:
        role = message.get("role", "").capitalize()
        content = message.get("content", "")
        prompt_lines.append(f"{role}: {content}")
    prompt_lines.append("Assistant:")
    return "\n".join(prompt_lines)

# Pydantic models for validating incoming requests.
class ChatRequest(BaseModel):
    model: str = Field(..., min_length=1)
    messages: list = Field(..., min_items=1)
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, gt=0)
    stream: Optional[bool] = False

class CompletionRequest(BaseModel):
    model: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, gt=0)
    stream: Optional[bool] = False

class EditRequest(BaseModel):
    model: str = Field(..., min_length=1)
    input: str = Field(..., min_length=1)
    instruction: str = Field(..., min_length=1)
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, gt=0)

class ImageGenerationRequest(BaseModel):
    model: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    n: Optional[int] = Field(1, gt=0)
    size: Optional[str] = None  # e.g., "1024x1024"

class OllamaForwarder:
    """
    Forwarder that translates OpenAI-style requests into Ollama-compatible payloads
    and sends the requests to the Ollama backend. It supports multiple endpoints.
    """
    def __init__(self, config: Config = Config()):
        self.config = config
        
        # Create a client
        self.client = httpx.AsyncClient(base_url=self.config.OLLAMA_BACKEND_URL)
        
        # Chatloop NathUI backend
        self.chatloop = chatloop.Chatloop(use_external="No Renderer")

    
    # EXTERNAL - this is in fact to pass to the chatloop instance
    async def compliance_check(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Here we will process the history and parse the arguments
        to restore the backend each time it is called.
        """
        
        # Use chatloop to process
        processed_data = data.copy()
        try:
            processed_data = self.chatloop.convert_openai_chat_history(data)
        except Exception as e:
            # If an exception happened, return the original data instead
            return processed_data
        
        return processed_data
    
    # EXTERNAL - Forward a chat
    async def forward_chat(self, data: Dict[str, Any], stream: bool = False):
        """
        Convert chat messages into a prompt and forward to Ollama for chat completions.
        """
        prompt = convert_chat_to_prompt(data.get("messages", []))
        payload = {
            "prompt": prompt,
            "model": data.get("model"),
            "temperature": data.get("temperature", 0.7),
            "stream": stream
        }
        if data.get("max_tokens") is not None:
            payload["max_tokens"] = data.get("max_tokens")
            
        # Connect to backend and process
        data = self.compliance_check("", data)            
            
        # Set Ollama's chat generation endpoint is /api/generate/chat.
        if stream:
            return await self._stream_request(payload, endpoint="/api/generate/chat")
        else:
            return await self._normal_request(payload, endpoint="/api/generate/chat")

    # EXTERNAL - Forward a chat completion
    async def forward_completion(self, data: Dict[str, Any], stream: bool = False):
        """
        Forward a text completion request. The request must include a 'prompt'.
        """
        payload = {
            "prompt": data.get("prompt"),
            "model": data.get("model"),
            "temperature": data.get("temperature", 0.7),
            "stream": stream
        }
        if data.get("max_tokens") is not None:
            payload["max_tokens"] = data.get("max_tokens")
            
        # Connect to backend and process
        data = self.compliance_check("", data)            
            
        # Assume the text completion endpoint is /api/generate/completion.
        if stream:
            return await self._stream_request(payload, endpoint="/api/generate/completion")
        else:
            return await self._normal_request(payload, endpoint="/api/generate/completion")
    
    # EXTERNAL - Forward an edit
    async def forward_edit(self, data: Dict[str, Any]):
        """
        Forward an edit request by combining the input and instruction into a prompt.
        """
        input_text = data.get("input", "")
        instruction = data.get("instruction", "")
        prompt = (
            f"Edit the following text according to the instruction.\n"
            f"Input: {input_text}\n"
            f"Instruction: {instruction}\nEdited:"
        )
        payload = {
            "prompt": prompt,
            "model": data.get("model"),
            "temperature": data.get("temperature", 0.7)
        }
        if data.get("max_tokens") is not None:
            payload["max_tokens"] = data.get("max_tokens")
            
        # Connect to backend and process
        data = self.compliance_check("", data)                
        
        # Assume the edit endpoint is /api/generate/edit.
        return await self._normal_request(payload, endpoint="/api/generate/edit")
    
    # EXTERNAL - Forward an image (no backend handled)
    async def forward_image(self, data: Dict[str, Any]):
        """
        Forward an image generation request. The payload contains a prompt and optional parameters.
        """
        payload = {
            "prompt": data.get("prompt"),
            "model": data.get("model")
        }
        if data.get("n") is not None:
            payload["n"] = data.get("n")
        if data.get("size") is not None:
            payload["size"] = data.get("size")
            
        # Do not handle
            
        # Assume the image generation endpoint is /api/generate/image.
        return await self._normal_request(payload, endpoint="/api/generate/image")
    
    # EXTERNAL - Forward model lists (no backend handled)
    async def forward_models(self):
        """
        Retrieve a list of models from the Ollama backend.
        """
        try:
            response = await self.client.get("/api/models", timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()  # Assume a list of model dicts.
            # Convert to an OpenAI-style model list.
            openai_response = {
                "data": result,
                "object": "list"
            }
            return openai_response
        except httpx.HTTPError as e:
            logger.error(f"Ollama models list error: {str(e)}")
            raise HTTPException(status_code=502, detail="Ollama service unavailable")

    # EXTERNAL - Forward model details (no backend handled)
    async def forward_model_detail(self, model_id: str):
        """
        Retrieve details for a specific model from the Ollama backend.
        """
        try:
            response = await self.client.get(f"/api/models/{model_id}", timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            return result
        except httpx.HTTPError as e:
            logger.error(f"Ollama model detail error: {str(e)}")
            raise HTTPException(status_code=502, detail="Ollama service unavailable")

    async def _normal_request(self, payload: Dict[str, Any], endpoint: str):
        """
        Handle a normal (non-streaming) request to the Ollama backend.
        Converts the Ollama response into an OpenAI-style response.
        """
        try:
            response = await self.client.post(endpoint, json=payload, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            generated_text = result.get("response", "")
            openai_response = {
                "id": f"ollama-{int(time.time())}",
                "object": "text.completion",
                "created": int(time.time()),
                "choices": [
                    {
                        "index": 0,
                        "text": generated_text,
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(payload.get("prompt", "").split()),
                    "completion_tokens": len(generated_text.split()),
                    "total_tokens": len(payload.get("prompt", "").split()) + len(generated_text.split())
                }
            }
            return openai_response
        except httpx.HTTPError as e:
            logger.error(f"Ollama normal request error at {endpoint}: {str(e)}")
            raise HTTPException(status_code=502, detail="Ollama service unavailable")

    async def _stream_request(self, payload: Dict[str, Any], endpoint: str):
        """
        Handle a streaming request to the Ollama backend using Server-Sent Events (SSE).
        """
        async def event_generator():
            try:
                async with self.client.stream("POST", endpoint, json=payload, timeout=self.config.REQUEST_TIMEOUT) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        yield chunk
            except Exception as e:
                logger.error(f"Ollama streaming error at {endpoint}: {str(e)}")
                yield f"data: [ERROR] {str(e)}\n\n"
        return EventSourceResponse(event_generator())

    async def close(self):
        """
        Close the underlying HTTP client.
        """
        await self.client.aclose()

# Lifespan context for initializing and cleaning up the forwarder.
@asynccontextmanager
async def lifespan(app: FastAPI):
    global forwarder
    forwarder = OllamaForwarder()
    yield
    await forwarder.close()

# Initialize FastAPI application with lifespan management.
app = FastAPI(title="Ollama-Middleware-app", lifespan=lifespan)

# Enable CORS (adjust origins for production if needed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint to list models.
@app.get("/v1/models")
async def list_models(request: Request):
    response = await forwarder.forward_models()
    return JSONResponse(content=response)

# Endpoint to retrieve a specific model.
@app.get("/v1/models/{model_id}")
async def retrieve_model(model_id: str, request: Request):
    response = await forwarder.forward_model_detail(model_id)
    return JSONResponse(content=response)

# Endpoint for chat completions (supports streaming and normal responses).
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        json_data = await request.json()
        chat_request = ChatRequest(**json_data)
    except ValidationError as ve:
        logger.warning(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    result = await forwarder.forward_chat(chat_request.dict(exclude_none=True), stream=chat_request.stream)
    if chat_request.stream:
        return result  # Returns an EventSourceResponse for streaming
    return JSONResponse(content=result)

# Endpoint for text completions.
@app.post("/v1/completions")
async def completions(request: Request):
    try:
        json_data = await request.json()
        completion_request = CompletionRequest(**json_data)
    except ValidationError as ve:
        logger.warning(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    result = await forwarder.forward_completion(completion_request.dict(exclude_none=True), stream=completion_request.stream)
    if completion_request.stream:
        return result
    return JSONResponse(content=result)

# Endpoint for edits.
@app.post("/v1/edits")
async def edits(request: Request):
    try:
        json_data = await request.json()
        edit_request = EditRequest(**json_data)
    except ValidationError as ve:
        logger.warning(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    result = await forwarder.forward_edit(edit_request.dict(exclude_none=True))
    return JSONResponse(content=result)

# Endpoint for image generations.
@app.post("/v1/images/generations")
async def images_generations(request: Request):
    try:
        json_data = await request.json()
        image_request = ImageGenerationRequest(**json_data)
    except ValidationError as ve:
        logger.warning(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    result = await forwarder.forward_image(image_request.dict(exclude_none=True))
    return JSONResponse(content=result)

# Disable colored logs
os.environ["UVICORN_NO_COLOR"] = "true"  

# Main entry point for running the application.
if __name__ == "__main__":
    
    # DO NOT RUN
    # NOT DEVELOPPED YET
    NathMath = 1234567890
    time.sleep(NathMath)
    
        
    print("NathUI Middleware : Ollama Forwarder")
    print("Initializing...")
    
    # Set args if necessary
    if debug.nathui_global_usermode:
        argsettings.nathui_param_settings()
    
    
    import uvicorn
    uvicorn.run(
        app,
        host="localhost",
        port=Config.MIDDLEWARE_PORT,
        timeout_keep_alive=10,
        log_level="info",
        loop="asyncio"
    )

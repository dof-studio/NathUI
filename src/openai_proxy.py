# openai_proxy.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Middleware ##################################################################

# Can NOT run in Ipython Environment!

## Auto Des ###################################################################
"""
A production-grade OpenAI middleware server that supports multiple endpoints
including model listing, text completions, chat completions (streaming and normal),
edits, and image generations. This middleware intercepts requests from the front-end,
applies pre-processing (e.g., compliance check, adding system messages), and then
forwards the request to either an upstream service or directly to the local OpenAI SDK.
"""
## Auto Des ###################################################################

import os
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import httpx
import openai
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

import debug
import argsettings
import params   # custom parameters module
import socks    # custom socket module
import chatloop # NathUI chat backend

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("OpenAI-Middleware")

# Configuration class reading from external params.
class Config:
    # OpenAI API key for local SDK usage.
    OPENAI_API_KEY = params.nathui_backend_apikey
    # Listening port for the middleware.
    MIDDLEWARE_PORT = socks.next_port(params.nathui_backend_middleware_starting_port)
    # Upstream backend host URL; if set, requests are forwarded to this host.
    UPSTREAM_HOST = params.nathui_backend_url
    # Request timeout in seconds.
    REQUEST_TIMEOUT = 6000

# OpenAI Middleware Engine by NathUI
class OpenAIMiddlewareEngine:
    """
    The middleware engine that processes incoming OpenAI-like requests,
    applies pre- and post-processing, and forwards them to either an upstream service
    or the local OpenAI SDK.
    """
    def __init__(self, config: Config = Config()):
        self.config = config
        
        # If an upstream host is provided, create an HTTP client for forwarding.
        if self.config.UPSTREAM_HOST:
            self.http_client = httpx.AsyncClient(base_url=f"{self.config.UPSTREAM_HOST}/")
        
        else:
            self.http_client = None
            # Set the API key for the local OpenAI SDK.
            openai.api_key = self.config.OPENAI_API_KEY
            
        # Use the openai package as the client for local requests.
        self.openai_client = openai
        
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
        processed_data = self.chatloop.convert_openai_chat_history(data)
        try:
            pass
        except Exception as e:
            # If an exception happened, return the original data instead
            return processed_data
        
        return processed_data
    
    # EXTERNAL - Process in from the frontend
    async def process_request(self, endpoint: str, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and modify the incoming request data. For instance, for chat completions,
        a system message is prepended if not already present.
        """
        if endpoint == "/v1/chat/completions" and "messages" in data:
            pass
        
        # Run a compliance check (or other pre-processing) here.
        data = await self.compliance_check(endpoint, data)
        return data
    
    # EXTERNAL - Process out from the backend
    async def process_response(self, endpoint: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and augment the response before returning to the front-end.
        """
        # Add a middleware notation
        response["middleware"] = {"processed_by": "Nathui-middleware"}
        return response
    
    # EXTERNAL - Forward a request
    async def forward_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        query_params: Optional[Dict[str, Any]] = None
    ):
        """
        Forward the request to the appropriate backend.
        If an upstream host is configured, forward via HTTP; otherwise, use the local OpenAI SDK.
        """
        data = data or {}
        original_data = data.copy()
        
        # Only for chats and completions
        if endpoint in ["/v1/chat/completions", "/v1/completions"]:
            
            # Get the original messages length
            original_data_msglen = len(original_data['messages'])
            
            # Pre-process the request.
            if debug.nathui_global_debug:
                pass
                # print("\nOriginally fetched: ", data, "\n")
            data = await self.process_request(endpoint, method, data)
            if debug.nathui_global_debug:
                pass
                # print("\nProcessed: ", data, "\n")
                
            # Handle if data is empty (must be after processed)
            if len(data) == 0:
                data["messages"] = {"rule":"assistant", "user":""}
                
            # If the processed data has more content than the original,
            # then generate the response internally.
            # The request content is in data["messages"][-1]["content"].
            if len(data["messages"]) > original_data_msglen:
                messages = data.get("messages", [])
                request_text = messages[-1].get("content", "") if messages else ""
                # Here you can replace the internal logic with your own response generation.
                internal_generated_text = request_text
                
                # Return as a streaming response if requested.
                # Suit for OpenWebUI
                if stream:
                    async def internal_stream_generator():
                        # Simulate streaming by splitting the response into tokens (here, words).
                        for word in internal_generated_text.split():
                            # Each chunk is a valid JSON object similar to OpenAI's SSE response.
                            chunk = {
                                "id": "internal_stream",
                                "choices": [{
                                    "delta": {"content": word + " "},
                                    "index": 0,
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                        # Final chunk to signal completion.
                        final_chunk = {
                            "id": "internal_stream",
                            "choices": [{
                                "delta": {},
                                "index": 0,
                                "finish_reason": "stop"
                            }]
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                    return StreamingResponse(internal_stream_generator(), media_type="text/event-stream")
                else:
                    # Return the complete response in JSON format.
                    return JSONResponse(content={
                        "choices": [{
                            "message": {
                                "role": "assistant",
                                "content": internal_generated_text
                            },
                            "index": 0,
                            "finish_reason": "stop"
                        }]
                    })
                
            # Or, generate by requesting to the backend,
            # Go rountinely
                
        # If an upstream host is configured, forward using HTTPx.
        if self.config.UPSTREAM_HOST:
            if stream:
                return await self._handle_streaming(method, endpoint, data, query_params)
            else:
                return await self._handle_normal_request(method, endpoint, data, query_params)
        else:
            # Use the local OpenAI SDK.
            return await self._handle_local_request(method, endpoint, data, stream)
        
    # Internal - Traits, process chunk byte class
    async def _handle_replace_chunk(self, chunk: bytes, replace_from: str, replace_to: str) -> bytes:
        """
        Process a chunk of SSE data:
        1. Decode the bytes to a UTF-8 string.
        2. If the string starts with the SSE prefix "data:", remove it.
        3. Parse the remaining text as JSON.
        4. In the JSON payload, for each choice, if a "delta" contains a key "reasoning_content",
           replace it with "content".
        5. Re-serialize the JSON and re-add the SSE formatting, then encode back to bytes.
        If any error occurs during processing, the original chunk is returned.
        """
        try:
            # Decode bytes to string
            text = chunk.decode("utf-8").strip()
            
            # Replace
            text_replaced = text.replace(replace_from, replace_to)
            
            # Return the result with SSE formatting as bytes
            return f"data: {text_replaced}\n\n".encode("utf-8")
        
        except Exception as e:
            # If processing fails, return the original chunk
            return chunk
        
    # Internal - Traits, convert chunk into a dict
    async def _handle_deconstruct_chunk(self, chunk: bytes) -> dict:
        """
        Process a chunk of SSE data:
        1. Decode the bytes to a UTF-8 string.
        """
        try:
            # Decode bytes to string
            text = chunk.decode("utf-8").strip()
            # Remove SSE prefix if present
            if text.startswith("data:"):
                text = text[5:].strip()
                
            # Parse the text as JSON
            payload = json.loads(text)

            return payload
        except Exception as e:
            # If processing fails, return the original chunk
            return {}
        
        
    # Called - Handle non-streaming requests via HTTP forwarding
    async def _handle_normal_request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any],
        query_params: Optional[Dict[str, Any]] = None
    ):
        """
        Handle non-streaming requests via HTTP forwarding.
        """
        try:
            client: httpx.AsyncClient = self.http_client  # type: ignore
            if method.upper() == "GET":
                response = await client.get(endpoint, params=query_params, timeout=self.config.REQUEST_TIMEOUT)
            elif method.upper() == "POST":
                response = await client.post(endpoint, json=data, params=query_params, timeout=self.config.REQUEST_TIMEOUT)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            response.raise_for_status()
            result = response.json()
            return await self.process_response(endpoint, result)
        except httpx.HTTPError as e:
            logger.error(f"Upstream error on {endpoint}: {str(e)}")
            raise HTTPException(status_code=502, detail="Upstream service unavailable")

    # Called - Handle streaming responses via HTTP forwarding using Server-Sent Events
    async def _handle_streaming(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any],
        query_params: Optional[Dict[str, Any]] = None
    ):
        """
        Forward streaming responses via HTTP without waiting for the complete response.
        This uses the raw bytes from the upstream response to yield chunks immediately.
        """
        self.think_end = 0
        
        async def _replace_reasoning_content(chunk):
            if self.think_end == 0:
                payload = self._handle_deconstruct_chunk()
                if "choices" in payload:
                    for choice in payload["choices"]:
                        delta = choice.get("delta", {})
                        if "reasoning_content" in delta:
                            val = delta["reasoning_content"]
                            if val == r"</think>":
                                self.think_end += 1
            # Replace or not
            if params.nathui_backend_stream_coer_dereasoning_content == True and self.think_end > 0:
                return self._handle_replace_chunk(chunk, "reasoning_content", "content")
            else:
                return chunk
        
        async def event_generator():
            try:
                client: httpx.AsyncClient = self.http_client  # type: ignore
                if method.upper() == "POST":
                    async with client.stream("POST", endpoint, json=data, params=query_params, timeout=self.config.REQUEST_TIMEOUT) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes():
                            # Immediately yield each received chunk
                            yield chunk
                elif method.upper() == "GET":
                    async with client.stream("GET", endpoint, params=query_params, timeout=self.config.REQUEST_TIMEOUT) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes():
                            yield chunk
                else:
                    raise HTTPException(status_code=405, detail="Method not allowed")
            except Exception as e:
                logger.error(f"Streaming error on {endpoint}: {str(e)}")
                yield f"data: [ERROR] {str(e)}\n\n".encode("utf-8")
        return StreamingResponse(event_generator(), media_type="text/event-stream")

        
    # Called - Handle the request using the local OpenAI SDK.
    async def _handle_local_request(
            self,
            method: str,
            endpoint: str,
            data: Dict[str, Any],
            stream: bool
        ):
            """
            Handle the request using the local OpenAI SDK. This method maps the endpoint
            to the corresponding OpenAI SDK function.
            """
            try:
                # Handle GET requests for models.
                if method.upper() == "GET":
                    if endpoint == "/v1/models":
                        # List models. Assumes an async variant (alist) if available.
                        if hasattr(self.openai_client.Model, "alist"):
                            result = await self.openai_client.Model.alist()
                        else:
                            result = await self.openai_client.Model.list()
                    elif endpoint.startswith("/v1/models/"):
                        # Retrieve a specific model.
                        model_id = endpoint.split("/")[-1]
                        if hasattr(self.openai_client.Model, "aretrieve"):
                            result = await self.openai_client.Model.aretrieve(model_id)
                        else:
                            result = await self.openai_client.Model.retrieve(model_id)
                    else:
                        raise HTTPException(status_code=404, detail="Endpoint not found")
                # Handle POST requests.
                elif method.upper() == "POST":
                    if endpoint == "/v1/chat/completions":
                        if stream:
                            stream_response = await self.openai_client.ChatCompletion.acreate(**data, stream=True)
                            async def event_generator():
                                async for chunk in stream_response:
                                    # Serialize each chunk as JSON.
                                    yield f"data: {json.dumps(chunk)}\n\n"
                            return EventSourceResponse(event_generator())
                        else:
                            result = await self.openai_client.ChatCompletion.acreate(**data)
                    elif endpoint == "/v1/completions":
                        if stream:
                            stream_response = await self.openai_client.Completion.acreate(**data, stream=True)
                            async def event_generator():
                                async for chunk in stream_response:
                                    yield f"data: {json.dumps(chunk)}\n\n"
                            return EventSourceResponse(event_generator())
                        else:
                            result = await self.openai_client.Completion.acreate(**data)
                    elif endpoint == "/v1/edits":
                        result = await self.openai_client.Edit.acreate(**data)
                    elif endpoint == "/v1/images/generations":
                        result = await self.openai_client.Image.acreate(**data)
                    else:
                        raise HTTPException(status_code=404, detail="Endpoint not implemented")
                else:
                    raise HTTPException(status_code=405, detail="Method not allowed")
    
                # Process non-streaming responses.
                if not stream:
                    # If the result is a model instance, convert it to a dictionary.
                    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
                    return await self.process_response(endpoint, result_dict)
            except Exception as e:
                logger.error(f"Local request error on {endpoint}: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

# FastAPI application initialization with lifespan management.
@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = OpenAIMiddlewareEngine()
    yield
    # Clean up HTTP client if it was created.
    if engine.http_client:
        await engine.http_client.aclose()

app = FastAPI(title="OpenAI-Middleware-app", lifespan=lifespan)

# Enable CORS for all origins (adjust as needed for production).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint to list all available models.
@app.get("/v1/models")
async def list_models(request: Request):
    query_params = dict(request.query_params)
    response = await engine.forward_request("GET", "/v1/models", query_params=query_params)
    return JSONResponse(content=response)

# Endpoint to retrieve a specific model by its ID.
@app.get("/v1/models/{model_id}")
async def retrieve_model(model_id: str, request: Request):
    endpoint = f"/v1/models/{model_id}"
    query_params = dict(request.query_params)
    response = await engine.forward_request("GET", endpoint, query_params=query_params)
    return JSONResponse(content=response)

# Endpoint for chat completions (supports streaming and non-streaming).
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    raw_body = await request.body()
    try:
        json_data = raw_body.decode("utf-8")
    except Exception as e:
        logger.error(f"Invalid JSON encoding: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON encoding")
    # Optionally, you can now parse the JSON after confirming the encoding:
    try:
        json_data = json.loads(json_data)
    except Exception as e:
        logger.error(f"Invalid JSON structure: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    stream = json_data.get("stream", False)
    response = await engine.forward_request("POST", "/v1/chat/completions", data=json_data, stream=stream)
    if stream:
        return response  # EventSourceResponse for streaming
    return JSONResponse(content=response)

# Endpoint for text completions.
@app.post("/v1/completions")
async def completions(request: Request):
    raw_body = await request.body()
    try:
        decoded_body = raw_body.decode("utf-8")
    except Exception as e:
        logger.error(f"Invalid JSON encoding in completions: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON encoding")
    try:
        json_data = json.loads(decoded_body)
    except Exception as e:
        logger.error(f"Invalid JSON structure in completions: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    stream = json_data.get("stream", False)
    response = await engine.forward_request("POST", "/v1/completions", data=json_data, stream=stream)
    if stream:
        return response
    return JSONResponse(content=response)

# Endpoint for edits.
@app.post("/v1/edits")
async def edits(request: Request):
    raw_body = await request.body()
    try:
        decoded_body = raw_body.decode("utf-8")
    except Exception as e:
        logger.error(f"Invalid JSON encoding in edits: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON encoding")
    try:
        json_data = json.loads(decoded_body)
    except Exception as e:
        logger.error(f"Invalid JSON structure in edits: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    response = await engine.forward_request("POST", "/v1/edits", data=json_data)
    return JSONResponse(content=response)

# Endpoint for image generations.
@app.post("/v1/images/generations")
async def images_generations(request: Request):
    raw_body = await request.body()
    try:
        decoded_body = raw_body.decode("utf-8")
    except Exception as e:
        logger.error(f"Invalid JSON encoding in image generations: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON encoding")
    try:
        json_data = json.loads(decoded_body)
    except Exception as e:
        logger.error(f"Invalid JSON structure in image generations: {raw_body} | Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    response = await engine.forward_request("POST", "/v1/images/generations", data=json_data)
    return JSONResponse(content=response)

# Disable colored logs
os.environ["UVICORN_NO_COLOR"] = "true"  

# Main entry point for running the application.
if __name__ == "__main__":
    
    print("NathUI Middleware : OpenAI Forwarder")
    print("Initializing...")
    
    import uvicorn
    uvicorn.run(
        app,
        host="localhost",
        port=Config.MIDDLEWARE_PORT,
        timeout_keep_alive=10,
        log_level="info",
        loop="asyncio"
    )
    
    # Requesting example
    r'''
    curl http://localhost:14514/v1/chat/completions \
      -H "Content-Type: application/json; charset=utf-8" \
      -d '{
        "model": "gemma-2-9b-it@q4_k_m",
        "messages": [ 
          { "role": "system", "content": "Always answer in rhymes." },
          { "role": "user", "content": "\\select 开发者 \\select 你的开发者是谁" }
        ], 
        "temperature": 0.7, 
        "max_tokens": -1,
        "stream": false
      }'

    '''

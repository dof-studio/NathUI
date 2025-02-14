# connect_backend.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# It is a FREE and OPEN SOURCED software
# See github.com/dof-studio/NathUI

# Backend #####################################################################

from openai import OpenAI

# a class
client = OpenAI(base_url="http://localhost:14514/v1", api_key="lm-studio")
model = "gemma-2-9b-it@q4_k_m"


# Get model list and switching models (auto selecting)
response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": r"\select 开发者 \select 你是谁开发的"},
    ],
    stream=True
)

# Stream
# Initialize an empty string to accumulate the output
cumulated_output = ""

# Iterate over each chunk in the streaming response
for chunk in response:
    # Each chunk may contain a 'choices' list with a 'delta' dict
    delta = chunk['choices'][0].get('delta', {})
    # Extract the content piece, if available
    content_piece = delta.get('content', '')
    # Append the content piece to the cumulative output
    cumulated_output += content_piece
    # Print the current cumulative output, overwriting the same line
    print(cumulated_output, end='\r', flush=True)

# Non-stream
# print(response.choices[0].message.content)
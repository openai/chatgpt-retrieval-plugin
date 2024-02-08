# Retrieval Plugin Function Calling Guide

This guide provides an overview of how to use the Retrieval Plugin with function calling in both the [Chat Completions API](https://platform.openai.com/docs/guides/function-calling) and the [Assistants API](https://platform.openai.com/docs/assistants/overview). This allows the model to decide when to use your functions (query, fetch, upsert) based on the conversation context.

## Table of Contents

- [Function Calling with Chat Completions](#function-calling-with-chat-completions)
- [Function Calling with Assistants API](#function-calling-with-assistants-api)
- [Tool Definitions](#tool-definitions)
- [Chat Completions Example](#chat-completions-example)
- [Assistants API Example](#assistants-api-example)

## Function Calling with Chat Completions

In a call to the chat completions API, you can describe functions and have the model generate a JSON object containing arguments to call one or many functions. The latest models (gpt-3.5-turbo-0125 and gpt-4-turbo-preview) have been trained to detect when a function should be called and to respond with JSON that adheres to the function signature.

You can define the functions for the Retrieval Plugin endpoints and pass them in as tools when you use the Chat Completions API with one of the latest models. The model will then intelligently call the functions. You can use function calling to write queries to your APIs, call the endpoint on the backend, and return the response as a tool message to the model to continue the conversation. The function definitions/schemas and an example can be found [here](#chat-completions-example).

## Function Calling with Assistants API

You can use the same function definitions with the OpenAI [Assistants API](https://platform.openai.com/docs/assistants/overview), specifically the [function calling in tool use](https://platform.openai.com/docs/assistants/tools/function-calling). The Assistants API allows you to build AI assistants within your own applications, leveraging models, tools, and knowledge to respond to user queries. The function definitions/schemas and an example can be found [here](/examples/function-calling/). The Assistants API natively supports retrieval from uploaded files, so you should use the Retrieval Plugin with function calling only if you want more granular control of your retrieval system (e.g. embedding chunk length, embedding model / size, etc.).

Parallel function calling is supported for both the Chat Completions API and the Assistants API. This means you can perform multiple tasks, such as querying something and saving something back to the vector database, in the same message.

Read more about function calling with the Retrieval Plugin [here](#assistants-api-example).

## Tool Definitions

Here is the tool definition for the `query` function:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "query",
            "description": "Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "title": "Query"
                                },
                                "filter": {
                                    "type": "object",
                                    "properties": {
                                        "document_id": {
                                            "type": "string",
                                            "title": "Document Id"
                                        },
                                        "source": {
                                            "type": "string",
                                            "enum": ["email", "file", "chat"],
                                        },
                                        "source_id": {
                                            "type": "string",
                                            "title": "Source Id"
                                        },
                                        "author": {
                                            "type": "string",
                                            "title": "Author"
                                        },
                                        "start_date": {
                                            "type": "string",
                                            "title": "Start Date"
                                        },
                                        "end_date": {
                                            "type": "string",
                                            "title": "End Date"
                                        }
                                    }
                                },
                                "top_k": {
                                    "type": "integer",
                                    "title": "Top K",
                                    "default": 3
                                }
                            },
                            "required": ["query"]
                        },
                        "description": "Array of queries to be processed",
                    },
                },
                "required": ["queries"],
            },
        }
    }
]
```

If using memory, as defined [here](/examples/memory/), then tools would include both the `query` and `upsert` functions:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "query",
            "description": "Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "title": "Query"
                                },
                                "filter": {
                                    "type": "object",
                                    "properties": {
                                        "document_id": {
                                            "type": "string",
                                            "title": "Document Id"
                                        },
                                        "source": {
                                            "type": "string",
                                            "enum": ["email", "file", "chat"],
                                        },
                                        "source_id": {
                                            "type": "string",
                                            "title": "Source Id"
                                        },
                                        "author": {
                                            "type": "string",
                                            "title": "Author"
                                        },
                                        "start_date": {
                                            "type": "string",
                                            "title": "Start Date"
                                        },
                                        "end_date": {
                                            "type": "string",
                                            "title": "End Date"
                                        }
                                    }
                                },
                                "top_k": {
                                    "type": "integer",
                                    "title": "Top K",
                                    "default": 3
                                }
                            },
                            "required": ["query"]
                        },
                        "description": "Array of queries to be processed",
                    },
                },
                "required": ["queries"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "upsert",
            "description": "Save chat information. Accepts an array of documents with text (potential questions + conversation text), metadata (source 'chat' and timestamp, no ID as this will be generated). Confirm with the user before saving, ask for more details/context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "documents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "title": "Id"
                                },
                                "text": {
                                    "type": "string",
                                    "title": "Text"
                                },
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "source": {
                                            "type": "string",
                                            "enum": ["email", "file", "chat"],
                                        },
                                        "source_id": {
                                            "type": "string",
                                            "title": "Source Id"
                                        },
                                        "url": {
                                            "type": "string",
                                            "title": "Url"
                                        },
                                        "created_at": {
                                            "type": "string",
                                            "title": "Created At"
                                        },
                                        "author": {
                                            "type": "string",
                                            "title": "Author"
                                        }
                                    }
                                }
                            },
                            "required": ["text"]
                        },
                        "description": "Array of documents to be upserted",
                    },
                },
                "required": ["documents"],
            },
        }
    },
]
```

## Chat Completions Example

Here is an example of how to use the [Chat Completions API with function calling](https://platform.openai.com/docs/guides/function-calling):

```python
# Step 1: send the conversation and available functions to the model
messages = [{"role": "user", "content": "What's the weather like in San Francisco, Tokyo, and Paris?"}]
tools = tools # as above
response = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=messages,
    tools=tools,
    tool_choice="auto",  # auto is default, but we'll be explicit
)
response_message = response.choices[0].message
tool_calls = response_message.tool_calls
# Step 2: check if the model wanted to call a function
if tool_calls:
    # Step 3: call the function
    # Note: the JSON response may not always be valid; be sure to handle errors
    available_functions = {
        "query": query,
    }  # only one function in this example, but you can have multiple
    messages.append(response_message)  # extend conversation with assistant's reply
    # Step 4: send the info for each function call and function response to the model
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_to_call = available_functions[function_name]
        function_args = json.loads(tool_call.function.arguments)
        function_response = function_to_call(
            queries=function_args.get("query"),
            filter=function_args.get("filter"),
        )
        messages.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response
    second_response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=messages,
    )  # get a new response from the model where it can see the function response
    print(second_response)
```

## Assistants API Example

For more information on how to use the Assistants API with function calling, refer to the [official documentation](https://platform.openai.com/docs/assistants/tools/function-calling). As mentioned above, the Assistants API natively supports retrieval from uploaded files, so you should use the Assistants API only if you want more granular control of your retrieval system (e.g. embedding chunk length, embedding model / size, etc). Here is a brief example:

First, define your functions when creating an Assistant:

```python
assistant = client.beta.assistants.create(
  instructions="You are a personal assistant with access to all of the user's personal documents.",
  model="gpt-4-turbo-preview",
  tools=tools # as defined above
)
```

When you initiate a Run with a user Message that triggers the function, the Run will enter a pending status. After it processes, the run will enter a requires_action state which you can verify by retrieving the Run. The model can provide multiple functions to call at once using parallel function calling:

```python
{
  "id": "run_abc123",
  "object": "thread.run",
  "assistant_id": "asst_abc123",
  "thread_id": "thread_abc123",
  "status": "requires_action",
  "required_action": {
    "type": "submit_tool_outputs",
    "submit_tool_outputs": {
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "query",
            "arguments": "{ \"queries\": <queries go here> }"
          }
        },
        {
          "id": "call_abc456",
          "type": "function",
          "function": {
            "name": "upsert",
            "arguments": "{ \"text\": <text goes here> }"
          }
        }
      ]
    }
  },
...
```

You can then complete the Run by [submitting the tool output](https://platform.openai.com/docs/api-reference/runs/submitToolOutputs) from the function(s) you call. Pass the tool_call_id referenced in the required_action object above to match output to each function call.

```python
run = client.beta.threads.runs.submit_tool_outputs(
  thread_id=thread.id,
  run_id=run.id,
  tool_outputs=[
      {
        "tool_call_id": call_ids[0],
        "output": [""""list of results here"""],
      },
      {
        "tool_call_id": call_ids[1],
        "output": [""""list of results here"""],
      },
    ]
)
```

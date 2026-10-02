import asyncio

from google import genai
from google.genai import types
from dotenv import load_dotenv

from config import LLM_API_KEY
from mcp_client import server_params
from mcp import ClientSession
from mcp.client.stdio import stdio_client


load_dotenv()


# Gemini client
client = genai.Client(api_key=LLM_API_KEY)


def clean_schema(schema):
    """
    Convert MCP JSON Schema into a Gemini-compatible schema.
    """

    if not isinstance(schema, dict):
        return schema

    cleaned = {}

    for key, value in schema.items():

        # Remove JSON Schema fields that Gemini does not accept
        if key in {
            "$schema",
            "additional_properties",
            "additionalProperties"
        }:
            continue

        # Recursively clean object properties
        if key == "properties" and isinstance(value, dict):

            cleaned["properties"] = {
                property_name: clean_schema(property_schema)
                for property_name, property_schema in value.items()
            }

        # Recursively clean array items
        elif key == "items" and isinstance(value, dict):

            cleaned["items"] = clean_schema(value)

        # Convert MCP any_of → Gemini anyOf
        elif key == "any_of" and isinstance(value, list):

            cleaned["anyOf"] = [
                clean_schema(item)
                for item in value
            ]

        # Convert MCP one_of → Gemini oneOf
        elif key == "one_of" and isinstance(value, list):

            cleaned["oneOf"] = [
                clean_schema(item)
                for item in value
            ]

        # Recursively clean nested dictionaries
        elif isinstance(value, dict):

            cleaned[key] = clean_schema(value)

        # Recursively clean lists
        elif isinstance(value, list):

            cleaned[key] = [
                clean_schema(item)
                if isinstance(item, dict)
                else item
                for item in value
            ]

        else:

            cleaned[key] = value

    return cleaned


def convert_mcp_tools(mcp_tools):
    """
    Convert GitHub MCP tools into Gemini function declarations.
    """

    function_declarations = []

    for tool in mcp_tools:

        parameters = clean_schema(tool.input_schema)

        function_declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "",
                parameters=parameters
            )
        )

    return types.Tool(
        function_declarations=function_declarations
    )


def format_mcp_result(result):
    """
    Convert MCP result into readable text.
    """

    if hasattr(result, "content"):

        parts = []

        for item in result.content:

            if hasattr(item, "text"):
                parts.append(item.text)

            else:
                parts.append(str(item))

        return "\n".join(parts)

    return str(result)


async def main():

    # Connect to GitHub MCP Server
    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # Initialize MCP connection
            await session.initialize()

            # Get available GitHub MCP tools
            tools_result = await session.list_tools()

            print(
                f"Loaded {len(tools_result.tools)} GitHub MCP tools."
            )

            # Convert MCP tools to Gemini tools
            github_tool = convert_mcp_tools(
                tools_result.tools
            )

            # Ask user
            user_request = input(
                "\nAsk your GitHub AI Assistant: "
            )

            # Send request to Gemini
            response = await client.aio.models.generate_content(
                model="gemini-3.8-flash",

                contents=user_request,

                config=types.GenerateContentConfig(

                    system_instruction=(
                        "You are an AI GitHub Developer Assistant. "
                        "You have access to GitHub through MCP tools. "
                        "Use the available GitHub tools when necessary "
                        "to answer the user's request."
                    ),

                    tools=[github_tool]
                )
            )

            # Check Gemini response
            candidate = response.candidates[0]
            content = candidate.content

            function_calls = []

            for part in content.parts:

                if part.function_call:

                    function_calls.append(
                        part.function_call
                    )

            # Gemini wants to call GitHub tools
            if function_calls:

                tool_response_parts = []

                for function_call in function_calls:

                    tool_name = function_call.name

                    arguments = dict(
                        function_call.args
                    )

                    print(
                        f"\nGemini selected tool: {tool_name}"
                    )

                    print(
                        f"Arguments: {arguments}"
                    )

                    # Execute GitHub MCP tool
                    result = await session.call_tool(
                        tool_name,
                        arguments
                    )

                    result_text = format_mcp_result(
                        result
                    )

                    print(
                        "\nGitHub MCP Result:"
                    )

                    print(result_text)

                    # Send GitHub result back to Gemini
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=tool_name,

                            response={
                                "result": result_text
                            }
                        )
                    )

                # Ask Gemini for the final answer
                final_response = await client.aio.models.generate_content(
                model="gemini-3.8-flash",

                    contents=[
                        user_request,
                        content,
                        *tool_response_parts
                    ],

                    config=types.GenerateContentConfig(

                        system_instruction=(
                            "You are an AI GitHub Developer Assistant. "
                            "Use the GitHub tool results to answer "
                            "the user's request clearly and accurately."
                        )
                    )
                )

                print("\nAssistant:")
                print(final_response.text)

            else:

                # Gemini answered without using a GitHub tool
                print("\nAssistant:")
                print(response.text)


if __name__ == "__main__":

    asyncio.run(main())
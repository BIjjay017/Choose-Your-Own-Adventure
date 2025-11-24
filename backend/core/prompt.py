STORY_PROMPT = """
You are a creative story writer who generates choose-your-own-adventure stories.

Your task:
- Create a complete branching story in strict JSON format.
- The JSON must match exactly the structure shown below.
- DO NOT wrap the output in ``` or any code block.
- DO NOT add explanations or extra text.
- Output ONLY raw JSON.

Story requirements:
- Title
- A rootNode with 2–3 options
- Each option leads to another node (2–3 levels deep)
- Ending nodes contain no `options` field or an empty array
- At least one winning ending

Here is the JSON schema you MUST follow:

{format_instructions}

Again: Output ONLY valid JSON. No markdown. No backticks. No comments.
"""


json_structure = """
{
  "title": "string",
  "rootNode": {
    "content": "string",
    "isEnding": false,
    "isWinningEnding": false,
    "options": [
      {
        "text": "string",
        "nextNode": {
          "content": "string",
          "isEnding": false,
          "isWinningEnding": false,
          "options": []
        }
      }
    ]
  }
}
"""
import json

def make_checklist(topic: str, items: int = 6):
    """
    Return a simple checklist for a given topic.
    Deterministic + structured, so the tool output is stable and easy to format.
    """
    items = max(3, min(items, 12))

    templates = [
        "Define the goal for '{topic}' in one sentence.",
        "List 5 key terms related to '{topic}'.",
        "Write 3 questions you want answered about '{topic}'.",
        "Find 2 credible sources and note 1 takeaway from each.",
        "Summarize '{topic}' in 5 bullet points.",
        "Create 3 examples or applications of '{topic}'.",
        "Identify 2 common misconceptions about '{topic}'.",
        "Teach '{topic}' in 3 sentences (as if to a beginner).",
        "Write a short glossary (5 items) for '{topic}'.",
        "Do a quick self-check: what is still unclear about '{topic}'?"
    ]

    checklist = []
    for i in range(items):
        checklist.append(templates[i % len(templates)].format(topic=topic))

    return {"topic": topic, "items": items, "checklist": checklist}

TOOLS = [
    {
        "type": "function",
        "name": "make_checklist",
        "description": "Generate a simple checklist (todo list) for a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "items": {"type": "integer"}
            },
            "required": ["topic"],
            "additionalProperties": False
        }
    }
]

def run_tools_loop(client, user_message: str) -> str:
    input_list = [{"role": "user", "content": user_message}]

    response = client.responses.create(
        model="gpt-4o-mini",
        tools=TOOLS,
        input=input_list,
        temperature=0.2
    )

    input_list += response.output

    for item in response.output:
        if item.type == "function_call" and item.name == "make_checklist":
            args = json.loads(item.arguments)
            tool_out = make_checklist(**args)

            input_list.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(tool_out)
            })

    response2 = client.responses.create(
        model="gpt-4o-mini",
        instructions="Use the tool output to answer clearly. Format as a checklist with bullet points. Do not invent extra items.",
        tools=TOOLS,
        input=input_list,
        temperature=0.2
    )
    return response2.output_text
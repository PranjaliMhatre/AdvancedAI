from openai import OpenAI

client = OpenAI()

resp = client.responses.create(
    model="gpt-5-nano",
    input="Summarize: LLMs are neural networks trained on text."
)

print(resp.output_text)
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()
project = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
client = project.get_openai_client()
r = client.responses.create(
    model=os.environ["TEXT_DEPLOYMENT"],
    input="Say hello from Umbu in five words.",
)
print(r.output_text)
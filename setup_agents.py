"""Registers Umbu's agents in Foundry. Run again whenever a prompt or context file changes:
each run creates a new agent version you can see in the Foundry portal."""
import os

from azure.ai.projects.models import PromptAgentDefinition

from umbu.context import load_context, load_prompt
from umbu.foundry import get_project

AGENTS = {
    "umbu-planner": {
        "model_env": "PLANNER_DEPLOYMENT",
        "prompt": "planner.md",
        "context": ["brand_voice.md", "approved_claims.md", "channel_specs.md"],
    },
    "umbu-copywriter": {
        "model_env": "TEXT_DEPLOYMENT",
        "prompt": "copywriter.md",
        "context": ["brand_voice.md", "approved_claims.md", "channel_specs.md"],
    },
    "umbu-art-director": {
        "model_env": "TEXT_DEPLOYMENT",
        "prompt": "art_director.md",
        "context": ["brand_voice.md", "channel_specs.md", "regulations.md"],
    },
    "umbu-claims-checker": {
        "model_env": "PLANNER_DEPLOYMENT",  # gpt-5: claims are the highest-risk judgment
        "prompt": "claims_checker.md",
        "context": ["approved_claims.md", "regulations.md"],
    },
    "umbu-brand-voice-checker": {
        "model_env": "TEXT_DEPLOYMENT",
        "prompt": "brand_voice_checker.md",
        "context": ["brand_voice.md"],
    },
}


def build_instructions(spec: dict) -> str:
    return load_prompt(spec["prompt"]) + "\n\n# Northwind context\n\n" + load_context(*spec["context"])


def main():
    project = get_project()
    for name, spec in AGENTS.items():
        agent = project.agents.create_version(
            agent_name=name,
            definition=PromptAgentDefinition(
                model=os.environ[spec["model_env"]],
                instructions=build_instructions(spec),
            ),
        )
        print(f"Registered {agent.name} (version {agent.version})")


if __name__ == "__main__":
    main()

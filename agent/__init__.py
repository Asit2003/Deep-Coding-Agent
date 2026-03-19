"""Agent package exports."""

__all__ = ["CodingOrchestrator"]


def __getattr__(name: str) -> object:
    if name == "CodingOrchestrator":
        from agent.orchestrator import CodingOrchestrator

        return CodingOrchestrator
    raise AttributeError(f"module 'agent' has no attribute '{name}'")

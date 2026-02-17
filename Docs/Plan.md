# Coding Agent Project Plan

## Problem Statement

I want to build a coding agent empowered with prompt and context engineering. This is a CLI based coding agent, and use openai as a llm to perform the task

## Approach

I will divide the task into multiple steps (sub agents and tools), then perform the independent tasks concurrently and then perform the dependent tasks if required and finalize the output

## Tech Stack

- python
- langgraph
- file system

## Common Sub-Agents

1. Orchestrator agent
2. Planning agent
3. Coding agent
4. Evaluation agent
5. etc.

## Common Tools

1. File create/delete/read/write/update
2. Web search tool (to fetch any relevant data about the packages or new tech stacks)
3. etc.
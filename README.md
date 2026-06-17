# Research Intelligence Assistant (RIA)

## Overview

Research Intelligence Assistant (RIA) is a Python-based benchmarking and research automation tool that helps users explore a technical topic and automatically generate structured benchmark reports.

The system combines scientific papers, patents, commercial solutions, and AI-powered analysis to create a research summary and benchmarking report that can support technology watch, competitive intelligence, innovation assessment, and R&D decision-making.

## Objectives

The goal of this project is to:

* Search and collect relevant scientific papers
* Search and collect relevant patents
* Rank and filter the most relevant sources
* Generate benchmark metrics automatically using LLMs
* Allow user review and validation
* Produce a structured Markdown benchmark report

## Current MVP Scope

### Data Sources

#### Patents

* SerpAPI Patent Search
* Real patent retrieval
* Patent title extraction
* Patent number extraction
* Assignee extraction
* Publication date extraction

#### Scientific Papers

* Semantic Scholar (in progress)

### AI Components

* Claude via OpenAI-compatible endpoint
* Structured JSON generation
* Relevance scoring
* Benchmark metric generation

## Architecture

```text
User Topic
    │
    ▼
Search Orchestrator
    │
    ├── Patent Adapter
    └── Paper Adapter
    │
    ▼
Ranking Engine
    │
    ▼
Metric Generation
    │
    ▼
User Validation
    │
    ▼
Report Generation
```

## Technology Stack

### Backend

* Python 3.11
* Pydantic v2
* AsyncIO
* HTTPX

### AI

* Claude
* OpenAI SDK
* Structured JSON prompting

### Testing

* Pytest
* Hypothesis

### External Services

* SerpAPI
* Semantic Scholar API

## Installation

Clone the repository:

```bash
git clone https://github.com/SajjadRostami/research-intelligence-assistant.git
cd research-intelligence-assistant
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment variables:

```bash
cp .env.example .env
```

Fill in:

```text
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://llm.aibricks.io/v1
SERPAPI_API_KEY=your_key
```

## Running Tests

### Patent Adapter

```bash
python test_serpapi_patents_live.py
```

### Unit Tests

```bash
pytest tests/ -v
```

## Project Status

### Completed

* Project structure
* Pydantic data models
* LLM client wrapper
* Search adapter framework
* SerpAPI patent adapter
* Unit testing infrastructure

### In Progress

* Semantic Scholar adapter
* Search orchestration
* Ranking engine

### Planned

* Benchmark metric generation
* User validation workflow
* Report generation
* Additional data sources

## Example Use Case

Input:

```text
XPBD soft body simulation algorithms
```

Output:

* Relevant patents
* Relevant scientific papers
* Benchmark metrics
* Executive summary
* Structured Markdown report

## Roadmap

### MVP

* Patent search
* Scientific paper search
* Ranking
* Report generation

### Future Versions

* Commercial solution discovery
* Tool discovery
* Multi-source benchmarking
* PDF export
* Interactive dashboard

## Author

Sajjad Rostami

PhD in Computer Science / XR / AI Systems

Research Intelligence Assistant was developed as part of an AI Engineering Bootcamp project focused on LLMs, RAG systems, and intelligent research automation.

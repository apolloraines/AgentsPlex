# Agent Integration Guide

## Overview

This guide describes how to integrate new agents into the CodeForge Review system. The system is designed to support multiple specialized review agents that can analyze code from different perspectives.

## Agent Architecture

### Core Components

1. **Agent Interface**: All agents must implement the base agent interface
2. **Communication Protocol**: Agents communicate via standardized message formats
3. **Review Pipeline**: Agents are invoked through the review orchestration system
4. **Result Aggregation**: Agent outputs are collected and merged

## Creating a New Agent

### Step 1: Define Agent Specification

Create a specification file in `agents/specs/` that defines your agent's capabilities:

```yaml
# Mini Agent Workflow Engine

A lightweight workflow orchestration system built with FastAPI, inspired by LangGraph. This engine allows you to define workflows as directed graphs with nodes, edges, conditional branching, and loops.

## Features

- **Node-based Execution**: Each node is a Python function that processes shared state
- **Conditional Branching**: Route workflow based on runtime conditions
- **Loop Support**: Execute nodes repeatedly until conditions are met
- **Async Execution**: Background task processing for non-blocking workflow runs
- **Tool Registry**: Register and manage reusable functions
- **State Management**: Pydantic-based state model with execution history
- **REST API**: FastAPI endpoints for graph creation and execution

## How to Run

### Prerequisites
```bash
pip install fastapi uvicorn pydantic
```

### Start the Server
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### Access API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### 1. Create a Graph
```bash
POST /graph/create
```

**Request Body:**
```json
{
  "nodes": ["node1", "node2", "node3"],
  "edges": {
    "node1": "node2",
    "node2": {
      "success": "node3",
      "retry": "node1",
      "fail": null
    }
  },
  "start_node": "node1"
}
```

**Response:**
```json
{
  "graph_id": "uuid-here",
  "message": "Graph created successfully"
}
```

### 2. Run a Workflow
```bash
POST /graph/run
```

**Request Body:**
```json
{
  "graph_id": "code-review-agent",
  "initial_state": {
    "code": "def func1(): pass\ndef func2(): pass",
    "quality_score": 10
  }
}
```

**Response:**
```json
{
  "run_id": "uuid-here",
  "status": "Submitted"
}
```

### 3. Check Workflow State
```bash
GET /graph/state/{run_id}
```

**Response:**
```json
{
  "run_id": "uuid-here",
  "graph_id": "code-review-agent",
  "status": "COMPLETED",
  "state": {
    "data": { /* workflow state */ },
    "history": [ /* execution log */ ]
  },
  "current_node": "quality_gate"
}
```

## Example Workflow: Code Review Agent

The engine comes pre-loaded with a code review workflow that demonstrates all core features:

### Workflow Steps:
1. **extract_functions**: Extracts function definitions from code
2. **check_complexity**: Calculates complexity score
3. **detect_issues**: Identifies code issues
4. **suggest_improvements**: Generates improvement suggestions
5. **quality_gate**: Conditional node that either:
   - Returns `"pass"` (score ≥ 80) → End workflow
   - Returns `"retry"` (score < 80) → Loop back to detect_issues

### Test the Example:
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/graph/run' \
  -H 'Content-Type: application/json' \
  -d '{
    "graph_id": "code-review-agent",
    "initial_state": {
      "code": "def func1(): pass\ndef func2(): pass\ndef func3(): pass",
      "quality_score": 10
    }
  }'
```

## What the Engine Supports

### Core Features
- ✅ **Graph Definition**: Define workflows with nodes and edges
- ✅ **State Flow**: Shared state that flows through nodes
- ✅ **Conditional Routing**: Branch based on runtime values
- ✅ **Loops**: Repeat execution until conditions are met
- ✅ **Async Execution**: Non-blocking background task execution
- ✅ **Tool Registry**: Register custom functions as workflow nodes
- ✅ **Execution History**: Complete log of node executions
- ✅ **Safety Guards**: Maximum step limit (50) to prevent infinite loops

### Edge Types
1. **Simple Edge**: Direct node-to-node connection
   ```python
   "node_a": "node_b"
   ```

2. **Conditional Edge**: Choose next node based on return value
   ```python
   "node_a": {
     "success": "node_b",
     "retry": "node_a",
     "fail": None  
   }
   ```

### Node Requirements
Nodes must:
- Accept `state: Dict` as parameter
- Return `str` for conditional routing (or `None` for default "next")
- Be registered in the tool registry before use

## Project Structure

```
.
├── main.py           # Main application file
├── README.md         # This file
└── requirements.txt  # Python dependencies (if needed)
```

## What I Would Improve With More Time

### High Priority
1. **Better Project Structure**
   - Separate files: `engine.py`, `models.py`, `api.py`, `workflows/`
   - Configuration management (env variables)
   - Proper logging framework (structured logging)

2. **Persistence Layer**
   - SQLite/PostgreSQL for graph and run storage
   - State snapshots for recovery
   - Run history and analytics

3. **Enhanced Error Handling**
   - Better error messages and validation
   - Node timeout handling
   - Graceful failure recovery
   - Retry mechanisms with exponential backoff

4. **Graph Validation**
   - Validate edges reference existing nodes
   - Detect cycles in non-loop scenarios
   - Ensure start_node exists
   - Schema validation for state

### Medium Priority
5. **Real-time Updates**
   - WebSocket endpoint for streaming execution logs
   - Server-Sent Events for status updates

6. **Observability**
   - Prometheus metrics (execution time, success/failure rates)
   - Distributed tracing (OpenTelemetry)
   - Detailed execution timeline

7. **Advanced Features**
   - Parallel node execution (fan-out/fan-in)
   - Subgraph support (reusable workflow components)
   - Dynamic graph modification during runtime
   - Human-in-the-loop nodes (wait for approval)

8. **Testing**
   - Unit tests for engine logic
   - Integration tests for API endpoints
   - End-to-end workflow tests
   - Load testing for concurrent workflows

### Lower Priority
9. **Developer Experience**
   - Graph visualization (Mermaid/Graphviz export)
   - CLI tool for graph management
   - Type safety improvements (TypedDict for state)
   - Better API documentation with examples

10. **Security & Production Readiness**
    - Authentication/authorization
    - Rate limiting
    - Input sanitization
    - Resource limits per workflow
    - Multi-tenancy support

## Design Decisions

### Why In-Memory Storage?
For this prototype, in-memory storage keeps things simple and demonstrates core workflow logic without database complexity. Production systems would need persistent storage.

### Why Background Tasks?
FastAPI's BackgroundTasks allows non-blocking workflow execution, so API responses are immediate while workflows run asynchronously.

### Why Simple Conditional Logic?
The string-based conditional routing (return "pass" vs "retry") is intentionally simple but extensible. More complex conditions could be added via predicate functions.

## License

This is a demo project for educational purposes.
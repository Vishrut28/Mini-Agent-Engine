import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class WorkflowState(BaseModel):
    """The shared state that flows between nodes."""
    data: Dict[str, Any] = Field(default_factory=dict)
    history: List[str] = Field(default_factory=list)

class GraphDefinition(BaseModel):
    nodes: List[str]
    edges: Dict[str, Union[str, Dict[str, Optional[str]]]]
    start_node: str
    
    @validator('start_node')
    def validate_start_node(cls, v, values):
        if 'nodes' in values and v not in values['nodes']:
            raise ValueError(f"start_node '{v}' must be in nodes list")
        return v
    
    @validator('edges')
    def validate_edges(cls, v, values):
        if 'nodes' not in values:
            return v
        
        nodes_set = set(values['nodes'])
        for source, target in v.items():
            if source not in nodes_set:
                raise ValueError(f"Edge source '{source}' not in nodes list")
            
            if isinstance(target, str):
                if target not in nodes_set:
                    raise ValueError(f"Edge target '{target}' not in nodes list")
            elif isinstance(target, dict):
                for outcome, dest in target.items():
                    if dest is not None and dest not in nodes_set:
                        raise ValueError(f"Edge target '{dest}' not in nodes list")
        return v

class WorkflowRun(BaseModel):
    run_id: str
    graph_id: str
    status: WorkflowStatus
    state: WorkflowState
    current_node: Optional[str] = None
    error: Optional[str] = None


graphs_db: Dict[str, GraphDefinition] = {}
runs_db: Dict[str, WorkflowRun] = {}
tool_registry: Dict[str, Callable] = {}


class WorkflowEngine:
    def __init__(self):
        self.registry = tool_registry
        self.max_steps = 50

    def register_tool(self, name: str, func: Callable):
        """Register a tool/node function."""
        self.registry[name] = func
        print(f"INFO:     Registered tool: {name}")

    async def execute_node(self, node_name: str, state: WorkflowState) -> str:
        """
        Executes a node and returns the next 'condition' key.
        Default return value is 'next' if node doesn't return a string.
        """
        if node_name not in self.registry:
            raise ValueError(f"Node '{node_name}' not found in registry.")
        
        func = self.registry[node_name]
        
        state.history.append(f"Executing: {node_name}")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(state.data)
            else:
                result = func(state.data)
            
            return result if isinstance(result, str) else "next"
        except Exception as e:
            state.history.append(f"Error in {node_name}: {str(e)}")
            raise

    async def run_workflow(self, graph: GraphDefinition, state: WorkflowState) -> None:
        """
        The core loop that moves state from node to node.
        """
        current_node = graph.start_node
        steps = 0
        
        while current_node:
            steps += 1
            
            if steps > self.max_steps:
                state.history.append(f"Max steps ({self.max_steps}) reached. Terminating.")
                break
            
            outcome = await self.execute_node(current_node, state)
            
            edge_config = graph.edges.get(current_node)
            
            if not edge_config:
                break
                
            if isinstance(edge_config, str):
                current_node = edge_config
            elif isinstance(edge_config, dict):
                current_node = edge_config.get(outcome)
                if current_node is None and outcome not in edge_config:
                    state.history.append(f"Warning: Outcome '{outcome}' not defined in edges for node. Ending workflow.")
                    break
        
        state.history.append("Workflow Completed.")

engine = WorkflowEngine()


def node_extract_functions(state: Dict) -> None:
    """Extract function definitions from code."""
    code = state.get("code", "")
    state["functions"] = [line for line in code.split("\n") if "def " in line]

def node_check_complexity(state: Dict) -> None:
    """Calculate complexity score based on number of functions."""
    state["complexity_score"] = len(state.get("functions", [])) * 2

def node_detect_issues(state: Dict) -> None:
    """Detect issues based on complexity."""
    complexity = state.get("complexity_score", 0)
    state["issues"] = ["Line 10: Too long"] if complexity > 5 else []

def node_suggest_improvements(state: Dict) -> None:
    """Suggest improvements and update quality score."""
    if state.get("issues"):
        state["suggestions"] = "Refactor logic to reduce complexity"
        state["quality_score"] = state.get("quality_score", 0) + 20
    else:
        state["suggestions"] = "Code looks good!"
        state["quality_score"] = 100

def node_quality_gate(state: Dict) -> str:
    """
    Quality gate that decides whether to pass or retry.
    Returns 'pass' if quality_score >= 80, otherwise 'retry'.
    """
    score = state.get("quality_score", 0)
    state["history"].append(f"Quality Gate: score={score}")
    
    if score >= 80:
        return "pass"
    else:
        return "retry"

engine.register_tool("extract_functions", node_extract_functions)
engine.register_tool("check_complexity", node_check_complexity)
engine.register_tool("detect_issues", node_detect_issues)
engine.register_tool("suggest_improvements", node_suggest_improvements)
engine.register_tool("quality_gate", node_quality_gate)


async def run_workflow_background(run_id: str):
    """Background task to execute workflow."""
    run = runs_db[run_id]
    run.status = WorkflowStatus.RUNNING
    
    try:
        graph = graphs_db[run.graph_id]
        await engine.run_workflow(graph, run.state)
        run.status = WorkflowStatus.COMPLETED
        
    except Exception as e:
        run.status = WorkflowStatus.FAILED
        run.error = str(e)
        run.state.history.append(f"Workflow failed: {str(e)}")
        print(f"ERROR:    Workflow {run_id} failed: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    default_graph_id = "code-review-agent"
    
    graphs_db[default_graph_id] = GraphDefinition(
        nodes=[
            "extract_functions",
            "check_complexity", 
            "detect_issues",
            "suggest_improvements",
            "quality_gate"
        ],
        start_node="extract_functions",
        edges={
            "extract_functions": "check_complexity",
            "check_complexity": "detect_issues",
            "detect_issues": "suggest_improvements",
            "suggest_improvements": "quality_gate",
            "quality_gate": {
                "retry": "detect_issues",  
                "pass": None               
            }
        }
    )
    print(f"INFO:     Pre-loaded graph '{default_graph_id}' successfully.")
    print(f"INFO:     Registered {len(tool_registry)} tools.")
    
    yield 
    
    print("INFO:     Shutting down workflow engine.")


app = FastAPI(
    title="Mini Agent Workflow Engine",
    description="A lightweight workflow orchestration system with nodes, edges, and conditional routing",
    version="1.0.0",
    lifespan=lifespan
)


class CreateGraphRequest(BaseModel):
    nodes: List[str]
    edges: Dict[str, Union[str, Dict[str, Optional[str]]]]
    start_node: str

class CreateGraphResponse(BaseModel):
    graph_id: str
    message: str

class RunGraphRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any]

class RunGraphResponse(BaseModel):
    run_id: str
    status: str


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "message": "Mini Agent Workflow Engine",
        "graphs_count": len(graphs_db),
        "runs_count": len(runs_db),
        "tools_count": len(tool_registry)
    }

@app.post("/graph/create", response_model=CreateGraphResponse)
async def create_graph(request: CreateGraphRequest):
    """
    Create a new workflow graph.
    
    The graph must have valid nodes, edges, and a start_node.
    Edges can be simple (string) or conditional (dict).
    """
    try:
        graph_id = str(uuid.uuid4())
        graphs_db[graph_id] = GraphDefinition(**request.dict())
        return CreateGraphResponse(
            graph_id=graph_id,
            message="Graph created successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/graph/run", response_model=RunGraphResponse)
async def run_graph(request: RunGraphRequest, background_tasks: BackgroundTasks):
    """
    Execute a workflow graph with the given initial state.
    
    Returns immediately with a run_id. Check status with GET /graph/state/{run_id}.
    """
    if request.graph_id not in graphs_db:
        raise HTTPException(status_code=404, detail=f"Graph '{request.graph_id}' not found")
    
    graph = graphs_db[request.graph_id]
    unregistered_nodes = [node for node in graph.nodes if node not in tool_registry]
    if unregistered_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"The following nodes are not registered: {unregistered_nodes}"
        )
    
    run_id = str(uuid.uuid4())
    initial_workflow_state = WorkflowState(data=request.initial_state)
    
    runs_db[run_id] = WorkflowRun(
        run_id=run_id,
        graph_id=request.graph_id,
        status=WorkflowStatus.PENDING,
        state=initial_workflow_state
    )
    
    background_tasks.add_task(run_workflow_background, run_id)
    
    return RunGraphResponse(run_id=run_id, status="Submitted")

@app.get("/graph/state/{run_id}", response_model=WorkflowRun)
async def get_run_state(run_id: str):
    """
    Get the current state of a workflow run.
    
    Returns the complete state including execution history and current status.
    """
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found")
    return runs_db[run_id]

@app.get("/graphs", response_model=Dict[str, GraphDefinition])
async def list_graphs():
    """List all available workflow graphs."""
    return graphs_db

@app.get("/tools", response_model=List[str])
async def list_tools():
    """List all registered tools/nodes."""
    return list(tool_registry.keys())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
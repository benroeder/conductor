# Conductor Architecture Documentation

## Overview

Conductor is a distributed testing framework designed to orchestrate tests across multiple networked systems. It follows a coordinator-worker pattern where a central conductor controls multiple players executing commands.

## System Components

### 1. Conductor (Coordinator)
- Central orchestration node
- Reads test configurations
- Manages test phases
- Collects results from players
- Controls test flow and synchronization

### 2. Player (Worker)
- Executes commands on remote systems
- Listens for instructions from conductor
- Returns execution results
- Maintains persistent connection for multiple test runs

## Architecture Diagrams

### System Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                        Test Environment                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                                            │
│  │   Conductor     │                                            │
│  │(Coordinator Node)│                                           │
│  │                 │                                            │
│  │ ┌─────────────┐ │                                            │
│  │ │  test.cfg   │ │                                            │
│  │ └─────────────┘ │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│           │ TCP Sockets (JSON Protocol v1)                      │
│           │                                                     │
│    ┌──────┴──────┬──────────┬──────────┐                        │
│    │             │          │          │                        │
│ ┌──▼───────┐ ┌──▼───────┐ ┌▼────────┐ ┌▼────────┐               │
│ │ Player 1 │ │ Player 2 │ │Player 3 │ │Player N │               │
│ │          │ │          │ │         │ │         │               │
│ │ ┌──────┐ │ │ ┌──────┐ │ │┌──────┐ │ │┌──────┐ │               │
│ │ │ DUT  │ │ │ │Server│ │ ││Client│ │ ││ Load │ │               │
│ │ │ .cfg │ │ │ │ .cfg │ │ ││ .cfg │ │ ││ Gen  │ │               │
│ │ └──────┘ │ │ └──────┘ │ │└──────┘ │ │└──────┘ │               │
│ └──────────┘ └──────────┘ └─────────┘ └─────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Communication Flow
```
Conductor                          Player
    │                                │
    ├──────── 1. Connect ──────────►│
    │         (Port 6970)            │
    │                                │
    ├──────── 2. Send Config ───────►│
    │◄─────── 3. ACK (OK) ───────────┤
    │                                │
    ├──────── 4. Send Phase ────────►│
    │◄─────── 5. ACK (OK) ───────────┤
    │                                │
    ├──────── 6. Send Run Cmd ──────►│
    │                                ├─── 7. Execute Steps
    │                                │    ├── Step 1
    │                                │    ├── Step 2
    │                                │    └── Step N
    │                                │
    │◄─────── 8. Send Results ───────┤
    │         (Port 6971)            │
    │                                │
    └────────────────────────────────┘
```

### Class Hierarchy
```
conductor/
    │
    ├── client.Client ─────────┬───► phase.Phase ────┬──► step.Step
    │   ├── config             │    ├── steps[]      │    ├── cmd
    │   ├── phases[]           │    ├── run()        │    ├── spawn
    │   ├── startup()          │    └── results[]    │    ├── timeout
    │   ├── run()              │                     │    └── run()
    │   ├── collect()          │                     │
    │   └── reset()            │                     │
    │                          │                     │
    ├── config.Config ─────────┘                     │
    │   ├── host                                     │
    │   └── port                                     │
    │                                                │
    └── retval.RetVal ◄──────────────────────────────┘
        ├── code (OK/ERROR/BAD_CMD/DONE)
        └── message
```

## Core Classes

### Reporter (`reporter.py`)
- Handles output formatting for test results
- Supports multiple output formats:
  - **Text**: Human-readable console output (default)
  - **JSON**: Machine-parseable structured data
- Abstracts output logic from core execution
- Enables easy addition of new formats (XML, HTML, etc.)

### Client (`client.py`)
- Represents a player from conductor's perspective
- Manages socket connection to a player
- Sends phases and receives results
- Handles configuration for each player

### Phase (`phase.py`)
- Container for multiple steps
- Four types: Startup, Run, Collect, Reset
- Executes steps sequentially (except Run phase)
- Returns aggregated results to conductor

### Step (`step.py`)
- Individual command execution unit
- Supports different execution modes:
  - **Normal**: Wait for completion
  - **Spawn**: Fire and forget
  - **Timeout**: Execute with time limit
- Uses subprocess for command execution

### RetVal (`retval.py`)
- Communication protocol for results
- Standardized return codes:
  - `RETVAL_OK` (0): Success
  - `RETVAL_ERROR` (1): Error
  - `RETVAL_BAD_CMD` (2): Unknown command
  - `RETVAL_DONE` (65535): Completion signal

## Communication Protocol

### JSON Protocol (v1)

The conductor uses a JSON-based protocol (transmitted in PLAIN TEXT) replacing the previous pickle implementation:

```
┌─────────────────────────────────────────────────────────────┐
│                   JSON Protocol Benefits                    │
├─────────────────────────────────────────────────────────────┤
│ • Security: No arbitrary code execution                     │
│ • Portability: Language-agnostic format                     │
│ • Debuggability: Human-readable messages                    │
│ • Versioning: Protocol version field for compatibility      │
│ • Size limits: Configurable max message size (default: 10MB)│
└─────────────────────────────────────────────────────────────┘
```

### Message Size Configuration

The maximum message size can be configured through:
1. **CLI Option**: `--max-message-size 20` (highest priority)
2. **Config File**: `max_message_size = 20` in `[Test]` or `[Coordinator]` section
3. **Default**: 10 MB if not specified

This allows handling larger payloads when needed while maintaining secure defaults.

### Message Types and Structure

```json
// Config Message
{
  "version": 1,
  "type": "config",
  "data": {
    "host": "192.168.1.10",
    "port": 6970
  }
}

// Phase Message
{
  "version": 1,
  "type": "phase",
  "data": {
    "name": "startup",
    "steps": ["mkdir -p /tmp/test", "echo 'Starting test'"]
  }
}

// RetVal Message
{
  "version": 1,
  "type": "retval",
  "data": {
    "retval": 0,
    "message": "Command executed successfully"
  }
}

// Run Command
{
  "version": 1,
  "type": "run",
  "data": "execute"
}
```

### Data Flow Diagram
```
┌────────────────────────────────────────────────────────────────┐
│                         Conductor                              │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  Config     │───►│   Client     │───►│  Socket Handler  │   │
│  │  Parser     │    │   Manager    │    │                  │   │
│  └─────────────┘    └──────────────┘    └─────────┬────────┘   │
│                                                   │            │
└───────────────────────────────────────────────────┼────────────┘
                                                    │
                              Network               │
                         ═══════════════════════════╪═══════════
                                                    │
┌───────────────────────────────────────────────────┼───────────┐
│                         Player                    │           │
│  ┌──────────────────┐    ┌──────────────┐    ┌────▼───────┐   │
│  │  Command         │◄───│   Phase      │◄───│  Socket    │   │
│  │  Executor        │    │   Handler    │    │  Listener  │   │
│  └────────┬─────────┘    └──────────────┘    └────────────┘   │
│           │                                                   │
│           ▼                                                   │
│  ┌──────────────────┐    ┌──────────────┐                     │
│  │   Subprocess     │───►│   Result     │                     │
│  │     Runner       │    │   Sender     │                     │
│  └──────────────────┘    └──────────────┘                     │
└───────────────────────────────────────────────────────────────┘
```

### Message Protocol Detail
```
┌─────────────────────────────────────────┐
│           Message Structure             │
├─────────────────────────────────────────┤
│  Bytes 0-3:  Message Length (uint32)    │
│  ┌───┬───┬───┬───┐                      │
│  │ L │ E │ N │   │  (Big Endian)        │
│  └───┴───┴───┴───┘                      │
├─────────────────────────────────────────┤
│  Bytes 4-N:  JSON Payload               │
│  ┌─────────────────────────────────┐    │
│  │ {                               │    │
│  │   "version": 1,                 │    │
│  │   "type": "phase",              │    │
│  │   "data": {                     │    │
│  │     "name": "startup",          │    │
│  │     "steps": [...]              │    │
│  │   }                             │    │
│  │ }                               │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### Sequence Diagram
```
Conductor          Player 1         Player 2         Player N
    │                 │                │                │
    │═══ Connect ════►│                │                │
    │◄══ Accept ══════│                │                │
    │                 │                │                │
    │══ Connect ══════════════════════►│                │
    │◄═ Accept ════════════════════════│                │
    │                 │                │                │
    │══ Config ══════►│                │                │
    │◄═ ACK ══════════│                │                │
    │                 │                │                │
    │══ Config ═══════════════════════►│                │
    │◄═ ACK ═══════════════════════════│                │
    │                 │                │                │
    │═ Phase(Startup)►│                │                │
    │◄═ ACK ══════════│                │                │
    │                 │                │                │
    │══ Phase(Startup)════════════════►│                │
    │◄═ ACK ═══════════════════════════│                │
    │                 │                │                │
    │══ Run ════════► │                │                │
    │                 │──Execute──┐    │                │
    │                 │◄──────────┘    │                │
    │                 │                │                │
    │══ Run ══════════════════════════►│                │
    │                 │                │──Execute──┐    │
    │                 │                │◄──────────┘    │
    │                 │                │                │
    │◄═ Results ══════│                │                │
    │◄═ Results ═══════════════════════│                │
    │                 │                │                │
    └─────────────────┴────────────────┴────────────────┘
```

### Ports
- **Command Port**: Receives instructions (default: 6970)
- **Results Port**: Sends execution results (default: 6971)

## Test Execution Flow

### State Machine
```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐
│ STARTUP ├────►│   RUN    ├────►│ COLLECT ├────►│  RESET  │
└─────────┘     └──────────┘     └─────────┘     └─────────┘
     │               │                 │               │
     ▼               ▼                 ▼               ▼
  Sequential      Parallel         Sequential     Sequential
  Execution       Execution        Execution      Execution
```

### Detailed Flow
```
┌─────────────────────────────────────────────────────────┐
│                    Conductor Start                      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              1. Initialization Phase                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │ • Read test.cfg                                  │   │
│  │ • Parse [Test] section for trials count          │   │
│  │ • Parse [Workers] section for player configs     │   │
│  │ • Load each player's configuration file          │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              2. Player Connection Phase                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │ For each player:                                 │   │
│  │   1. Create socket to player:cmdport             │   │
│  │   2. Send Config object                          │   │
│  │   3. Receive ACK                                 │   │
│  │   4. Store connection reference                  │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              3. Test Execution Loop                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │ For trial in range(trials):                      │   │
│  │   For phase in [Startup, Run, Collect, Reset]:   │   │
│  │     a. Send phase to all players                 │   │
│  │     b. Send run command to all players           │   │
│  │     c. Collect results from all players          │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  4. Cleanup Phase                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ • Close all socket connections                   │   │
│  │ • Aggregate test results                         │   │
│  │ • Generate reports (if configured)               │   │
│  │ • Exit with appropriate code                     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Configuration Structure

### Test Configuration (`test.cfg`)
```ini
[Test]
trials: 1              # Number of test iterations

[Workers]
client1: dut.cfg       # Player configuration files
client2: server.cfg
```

### Player Configuration (`player.cfg`)
```ini
[Coordinator]
player: 192.168.1.10   # Player's IP address
conductor: 192.168.1.1 # Conductor's IP address
cmdport: 6970          # Command port
resultsport: 6971      # Results port

[Startup]
step1: mkdir -p /tmp/test

[Run]
step1: spawn:iperf -s
step2: timeout30:ping -c 100 target

[Collect]
step1: tar -czf results.tgz /tmp/test

[Reset]
step1: rm -rf /tmp/test
```

## Execution Modes

### Phase Execution Patterns
```
STARTUP Phase (Sequential)          RUN Phase (Parallel)
─────────────────────────          ─────────────────────
                                   
Step 1 ──────►│                    Step 1 ────┐
              ▼                               │
Step 2 ──────►│                    Step 2 ────┼────► All
              ▼                               │      Start
Step 3 ──────►│                    Step 3 ────┤      Together
              ▼                               │
            Done                   Step N ────┘

COLLECT Phase (Sequential)          RESET Phase (Sequential)
──────────────────────────         ───────────────────────

Step 1 ──────►│                    Step 1 ──────►│
              ▼                                  ▼
Step 2 ──────►│                    Step 2 ──────►│
              ▼                                  ▼
            Done                               Done
```

### Command Execution Types
```
┌─────────────────────────────────────────────────────────────┐
│                    Step Execution Modes                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Normal Execution (Default)                              │
│     ┌──────────┐                                            │
│     │ Command  │──► Wait for ──► Get Exit ──► Continue      │
│     └──────────┘    Completion     Code                     │
│                                                             │
│  2. Spawn Execution (spawn: prefix)                         │
│     ┌──────────┐                                            │
│     │ Command  │──► Start ──► Continue                      │
│     └──────────┘    Process    (Don't Wait)                 │
│                                                             │
│  3. Timeout Execution (timeout<N>: prefix)                  │
│     ┌──────────┐                                            │
│     │ Command  │──► Start ──► Wait Max ──► Kill if          │
│     └──────────┘             N seconds     Still Running    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Example Step Configurations
```ini
[Startup]
# Normal execution - waits for completion
step1: mkdir -p /tmp/test
step2: cp config.txt /tmp/test/

[Run]
# Spawn execution - fire and forget
step1: spawn:iperf3 -s -D
step2: spawn:tcpdump -i eth0 -w capture.pcap

# Timeout execution - max 30 seconds
step3: timeout30:wget http://example.com/large_file.zip

[Collect]
# Normal execution again
step1: tar -czf results.tgz /tmp/test
step2: scp results.tgz conductor:/results/

[Reset]
# Cleanup
step1: killall iperf3
step2: rm -rf /tmp/test
```

## Error Handling

### Network Failures
- Socket exceptions caught and logged
- Player connection failures reported
- Conductor continues with remaining players

### Command Failures
- Non-zero exit codes captured
- Stderr output included in results
- Failures don't stop phase execution

### Timeout Handling
- Processes killed after timeout
- Timeout status returned in results
- Cleanup of zombie processes

## Scalability Considerations

### Current Limitations
- Synchronous communication with players
- Sequential player setup
- Single-threaded conductor

### Potential Improvements
- Asynchronous player communication
- Parallel phase distribution
- Result streaming vs batch collection
- Player health monitoring

## Security Notes

⚠️ **IMPORTANT: Conductor is NOT secure for internet use!** ⚠️

### Critical Security Limitations
- **NO ENCRYPTION**: All network traffic is PLAINTEXT
- **NO AUTHENTICATION**: Anyone who can connect can execute commands
- **FULL SYSTEM ACCESS**: Players execute arbitrary shell commands
- **PRIVATE NETWORKS ONLY**: Must be used behind firewalls on isolated test networks

### Current State
- **JSON Protocol**: Replaced insecure pickle serialization
- **Protocol Versioning**: Ensures compatibility and security
- **Size Limits**: 10MB max message size prevents DoS
- **No Code Execution**: JSON cannot execute arbitrary code
- No authentication between conductor/player
- Plaintext communication (but safe JSON)
- Command execution still requires trust

### Security Improvements Made
```
┌─────────────────────────────────────────────────────────────┐
│                 Security Evolution                          │
├─────────────────┬───────────────────────────────────────────┤
│ Previous (v0)   │ Current (v1)                              │
├─────────────────┼───────────────────────────────────────────┤
│ Pickle Protocol │ JSON Protocol                             │
│ • Code execution│ • No code execution                       │
│ • Python-only   │ • Language agnostic                       │
│ • Security risk │ • Safe serialization                      │
│ • No validation │ • Schema validation                       │
│ • No size limit │ • 10MB size limit                         │
└─────────────────┴───────────────────────────────────────────┘
```

### Remaining Recommendations
- Add TLS encryption for confidentiality
- Implement authentication tokens
- Command whitelisting option
- Audit logging
- Consider mTLS for mutual authentication

## Modern CLI Features

### Enhanced Command-Line Interface
```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Architecture                         │
├─────────────────────────────────────────────────────────────┤
│ Conductor CLI (conduct)                                     │
│ ├── --trials N         Override trial count                 │
│ ├── --phases PHASE     Run specific phases only             │
│ ├── --clients CLIENT   Test specific clients                │
│ ├── --dry-run          Preview execution plan               │
│ ├── --format FORMAT    Output format (text/json)            │
│ ├── --output FILE      Write results to file                │
│ ├── --verbose/-v       Debug logging                        │
│ └── --quiet/-q         Suppress output                      │
│                                                             │
│ Player CLI (player)                                         │
│ ├── --log-file FILE    Log to file                          │
│ ├── --verbose/-v       Debug logging                        │
│ └── config.cfg         Configuration file                   │
└─────────────────────────────────────────────────────────────┘
```

### Output Formats via Reporter
```
Text Format (Default)          JSON Format (--format json)
─────────────────────         ──────────────────────────
                              
Phase: startup                 {
  Client: web_server            "phase": "startup",
  Step 1: OK                    "results": [
  Step 2: OK                      {
                                    "client": "web_server",
Phase: run                          "steps": [
  Client: web_server                  {"index": 1, "status": "OK"},
  Step 1: OK                          {"index": 2, "status": "OK"}
  Output: Server started            ]
                                  }
                                ]
                              }
```

## Extension Points

### Custom Phases
- Extend Phase class
- Add new phase types beyond four defaults
- Custom execution strategies

### Result Processing
- Extend RetVal for richer data
- Add result aggregation plugins
- Real-time result streaming
- Custom Reporter formats (XML, HTML, CSV)

### Player Capabilities
- Platform-specific command adapters
- Resource monitoring integration
- Custom step executors
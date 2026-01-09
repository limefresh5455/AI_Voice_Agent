# Complete Go Code Walkthrough - Line by Line

## Table of Contents
1. [main.go](#maingo) - Application Entry Point
2. [config/config.go](#configconfiggo) - Configuration Management
3. [handlers/websocket.go](#handlerswebsocketgo) - WebSocket Handler
4. [services/session_manager.go](#servicessession_managergo) - Session Coordination
5. [services/redis.go](#servicesredisgo) - Redis Client
6. [services/deepgram_stt.go](#servicesdeepgram_sttgo) - Speech-to-Text
7. [services/deepgram_tts.go](#servicesdeepgram_ttsgo) - Text-to-Speech
8. [services/llm_client.go](#servicesllm_clientgo) - LLM HTTP Client

---

## main.go

**Purpose**: The entry point of the application. Sets up the HTTP server, routes, and graceful shutdown.

```go
// filepath: streaming-gateway/main.go
package main
```
**Line 1**: Every Go file starts with a `package` declaration. `package main` is special - it tells Go this is an executable program (not a library). Only `main` packages can be run as programs.

```go
import (
    "context"
    "fmt"
    "log"
    "mime"
    "net/http"
    "os"
    "os/signal"
    "path/filepath"
    "syscall"
    "time"

    "github.com/legalcorner/ai-voice-streaming/internal/config"
    "github.com/legalcorner/ai-voice-streaming/internal/handlers"
    "github.com/legalcorner/ai-voice-streaming/internal/services"
)
```
**Lines 3-18**: Import statements bring in code from other packages:
- `context`: Used for cancellation and timeouts (like "stop doing this now")
- `fmt`: Formatting and printing (like Python's `print()`)
- `log`: Logging messages
- `mime`: MIME type detection (e.g., `.js` = `application/javascript`)
- `net/http`: HTTP server and client
- `os`: Operating system functions (environment variables, file operations)
- `os/signal`: Listen for OS signals like CTRL+C
- `path/filepath`: File path manipulation (works on Windows/Mac/Linux)
- `syscall`: Low-level system calls
- `time`: Time and duration operations

The last 3 imports are from our own code (local packages).

```go
func main() {
```
**Line 20**: `func main()` is the entry point - like `if __name__ == "__main__":` in Python. When you run the program, this function executes first.

```go
    // Load configuration from environment variables
    cfg := config.Load()
```
**Line 22**: Call `config.Load()` to read environment variables (like `PORT`, `DEEPGRAM_API_KEY`). The `:=` operator declares a new variable AND assigns to it (shorthand for `var cfg = config.Load()`).

```go
    // Initialize services
    log.Println("Initializing services...")
```
**Line 25**: Print a log message. `log.Println()` is like `print()` in Python but includes timestamps.

```go
    // Redis client
    redisClient := services.NewRedisClient(cfg.RedisURL)
    defer redisClient.Close()
```
**Lines 28-29**: 
- Create a Redis client connection
- `defer redisClient.Close()` means "when `main()` exits, close the Redis connection". `defer` schedules a function to run at the end of the current function (like Python's context managers or `finally` blocks).

```go
    // Session manager
    sessionManager := services.NewSessionManager(redisClient, cfg.PythonServiceURL)
```
**Line 32**: Create a session manager that coordinates between Redis and the Python LLM service.

```go
    // WebSocket handler
    wsHandler := handlers.NewWebSocketHandler(cfg.DeepgramAPIKey, sessionManager)
```
**Line 35**: Create the WebSocket handler that manages client connections, STT, and TTS.

```go
    // Setup HTTP routes
    mux := http.NewServeMux()
```
**Line 38**: Create a new HTTP router. `ServeMux` is like Flask's app router - it maps URLs to handler functions.

```go
    // WebSocket endpoint
    mux.HandleFunc("/ws", wsHandler.HandleWebSocket)
```
**Line 41**: Register a route: when someone connects to `/ws`, call `wsHandler.HandleWebSocket`. This is like `@app.route('/ws')` in Flask.

```go
    // Health check endpoint
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`{"status":"healthy"}`))
    })
```
**Lines 44-47**: Define an inline function (anonymous function/lambda) for the `/health` endpoint:
- `w http.ResponseWriter` - where we write the HTTP response (like Flask's `return`)
- `r *http.Request` - the incoming HTTP request (like Flask's `request`)
- `w.WriteHeader(http.StatusOK)` - set HTTP status code 200
- `w.Write([]byte(...))` - write the response body. `[]byte` converts a string to bytes (Go's HTTP needs bytes, not strings)

```go
    // Serve static files from web directory with proper MIME types
    webDir := "./web"
    fileServer := http.FileServer(http.Dir(webDir))
```
**Lines 50-51**: 
- Set the directory containing HTML/JS files
- Create a file server that serves files from that directory (like `app.static_folder` in Flask)

```go
    mux.Handle("/", http.StripPrefix("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
```
**Line 53**: Register the root route `/` with a custom handler:
- `http.StripPrefix("/", ...)` - removes the `/` prefix from the URL (cosmetic)
- `http.HandlerFunc(...)` - wraps our function to match Go's `Handler` interface

```go
        // Get the file path
        filePath := filepath.Join(webDir, r.URL.Path)
```
**Line 55**: Build the full file path by joining the web directory with the requested URL path. Example: `./web` + `/client.js` = `./web/client.js`

```go
        // If path is a directory or empty, serve index.html
        if r.URL.Path == "/" || r.URL.Path == "" {
            filePath = filepath.Join(webDir, "index.html")
        }
```
**Lines 58-60**: If someone visits `/` (root), serve `index.html` instead.

```go
        // Detect MIME type from file extension
        ext := filepath.Ext(filePath)
        if mimeType := mime.TypeByExtension(ext); mimeType != "" {
            w.Header().Set("Content-Type", mimeType)
        }
```
**Lines 63-66**: 
- Get the file extension (`.js`, `.html`, etc.)
- Look up the correct MIME type for that extension
- If found, set the `Content-Type` header (this fixes the JavaScript MIME type issue!)

```go
        // Serve the file
        fileServer.ServeHTTP(w, r)
    })))
```
**Lines 69-70**: Finally, let the file server handle the request (actually read and send the file).

```go
    // Create HTTP server
    server := &http.Server{
        Addr:    fmt.Sprintf("%s:%s", cfg.Host, cfg.Port),
        Handler: mux,
    }
```
**Lines 73-76**: Create an HTTP server configuration:
- `&http.Server{...}` creates a pointer to a new Server struct (structs are like classes in other languages)
- `Addr`: where to listen (e.g., `0.0.0.0:8080`)
- `Handler`: the router that handles requests (our `mux`)

```go
    // Start server in a goroutine
    go func() {
        log.Printf("Starting server on %s", server.Addr)
        if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("Server error: %v", err)
        }
    }()
```
**Lines 79-84**: 
- `go func() { ... }()` starts a **goroutine** (lightweight thread) to run the server in the background
- This lets the main thread continue to set up graceful shutdown
- `server.ListenAndServe()` blocks and listens for incoming connections
- `if err := ...` checks for errors and exits if there's a fatal error (except for expected shutdown)

```go
    // Graceful shutdown
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
```
**Lines 87-89**: 
- `make(chan os.Signal, 1)` creates a **channel** (like a queue) that can hold 1 signal
- Channels are Go's way of communicating between goroutines (think: thread-safe queue)
- `signal.Notify(quit, ...)` tells OS to send SIGINT (Ctrl+C) or SIGTERM (Docker stop) to this channel
- `<-quit` **blocks** until a signal arrives (waits here until user presses Ctrl+C)

```go
    log.Println("Shutting down server...")
```
**Line 91**: When we get here, a shutdown signal was received.

```go
    // Give outstanding requests 30 seconds to complete
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
```
**Lines 94-95**: 
- Create a context with a 30-second timeout
- Context is Go's way of saying "you have 30 seconds to finish, then I'm cutting you off"
- `defer cancel()` ensures we clean up the context when done

```go
    if err := server.Shutdown(ctx); err != nil {
        log.Fatalf("Server forced to shutdown: %v", err)
    }
```
**Lines 97-99**: 
- Gracefully shut down the server (finish current requests, don't accept new ones)
- If it takes longer than 30 seconds, force shutdown and exit with error

```go
    log.Println("Server exited")
}
```
**Lines 101-102**: Program ends cleanly.

---

## config/config.go

**Purpose**: Load and validate configuration from environment variables.

```go
// filepath: streaming-gateway/internal/config/config.go
package config
```
**Line 1**: This is the `config` package (a library, not an executable).

```go
import (
    "log"
    "os"
)
```
**Lines 3-6**: Import what we need:
- `log`: For error messages
- `os`: To read environment variables

```go
// Config holds all application configuration
type Config struct {
    Host              string
    Port              string
    DeepgramAPIKey    string
    RedisURL          string
    PythonServiceURL  string
    Environment       string
}
```
**Lines 8-16**: Define a `Config` struct (like a class with only fields, no methods):
- `type Config struct` declares a new type called `Config`
- Each line is a field with a name and type
- All fields are strings in this case
- Structs are Go's way of grouping related data

```go
// Load reads configuration from environment variables
func Load() *Config {
```
**Line 19**: Define a function that returns a **pointer** to Config (`*Config`):
- `*` means "pointer to" (memory address)
- Pointers are efficient - we pass the address instead of copying the whole struct
- Like passing by reference in other languages

```go
    cfg := &Config{
        Host:              getEnv("HOST", "0.0.0.0"),
        Port:              getEnv("PORT", "8080"),
        DeepgramAPIKey:    getEnv("DEEPGRAM_API_KEY", ""),
        RedisURL:          getEnv("REDIS_URL", "redis://localhost:6379/0"),
        PythonServiceURL:  getEnv("PYTHON_SERVICE_URL", "http://localhost:8001"),
        Environment:       getEnv("ENVIRONMENT", "development"),
    }
```
**Lines 20-27**: 
- `&Config{...}` creates a Config struct and returns its address (pointer)
- Each field calls `getEnv(name, default)` to get an environment variable or use a default
- This is like Python's `os.getenv("HOST", "0.0.0.0")`

```go
    // Validate required fields
    if cfg.DeepgramAPIKey == "" {
        log.Fatal("DEEPGRAM_API_KEY environment variable is required")
    }
```
**Lines 30-32**: 
- Check if the API key is empty
- `log.Fatal()` prints an error and exits the program (like `sys.exit(1)`)
- This ensures we don't run without required configuration

```go
    return cfg
}
```
**Line 34**: Return the pointer to the Config struct.

```go
// getEnv reads an environment variable or returns a default value
func getEnv(key, defaultValue string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return defaultValue
}
```
**Lines 37-42**: Helper function to get environment variables:
- `os.Getenv(key)` reads the environment variable
- The `if value := ...; value != ""` pattern is called "short variable declaration with condition"
- It declares `value`, assigns it, and checks it in one line
- If the variable exists and isn't empty, return it; otherwise return the default

---

## handlers/websocket.go

**Purpose**: Handle WebSocket connections, coordinate STT/TTS, and session management.

```go
// filepath: streaming-gateway/internal/handlers/websocket.go
package handlers
```
**Line 1**: This is the `handlers` package.

```go
import (
    "context"
    "encoding/base64"
    "encoding/json"
    "log"
    "sync"
    "time"

    "github.com/google/uuid"
    "github.com/gorilla/websocket"

    "github.com/legalcorner/ai-voice-streaming/internal/services"
)
```
**Lines 3-14**: Imports:
- `context`: For cancellation
- `encoding/base64`: Encode/decode base64 (for audio data)
- `encoding/json`: JSON parsing (like Python's `json` module)
- `sync`: Synchronization primitives (locks, wait groups)
- `time`: Time operations
- `uuid`: Generate unique IDs
- `websocket`: WebSocket library (third-party package)
- Our own `services` package

```go
// Message types sent between client and server
type Message struct {
    Type       string `json:"type"`
    Data       string `json:"data,omitempty"`
    Text       string `json:"text,omitempty"`
    Speaker    string `json:"speaker,omitempty"`
    SampleRate int    `json:"sampleRate,omitempty"`
}
```
**Lines 16-23**: Define a struct for WebSocket messages:
- The backtick strings (`` `json:"type"` ``) are **struct tags** - they tell Go how to convert to/from JSON
- `omitempty` means "skip this field if it's empty" in JSON
- This is like Python's `@dataclass` with JSON serialization

```go
// WebSocketHandler handles WebSocket connections
type WebSocketHandler struct {
    deepgramAPIKey string
    sessionManager *services.SessionManager
    upgrader       websocket.Upgrader
}
```
**Lines 25-30**: Define the WebSocket handler struct:
- Holds configuration and dependencies
- `upgrader` converts HTTP connections to WebSocket connections

```go
// NewWebSocketHandler creates a new WebSocket handler
func NewWebSocketHandler(deepgramAPIKey string, sessionManager *services.SessionManager) *WebSocketHandler {
    return &WebSocketHandler{
        deepgramAPIKey: deepgramAPIKey,
        sessionManager: sessionManager,
        upgrader: websocket.Upgrader{
            CheckOrigin: func(r *http.Request) bool {
                return true // Allow all origins in development
            },
        },
    }
}
```
**Lines 32-42**: Constructor function (like `__init__` in Python):
- Takes dependencies as parameters
- Creates and returns a new handler
- `CheckOrigin: func() { return true }` allows WebSocket connections from any origin (in production, you'd restrict this)

```go
// HandleWebSocket handles WebSocket connections
func (h *WebSocketHandler) HandleWebSocket(w http.ResponseWriter, r *http.Request) {
```
**Line 45**: 
- `func (h *WebSocketHandler)` is a **method** on WebSocketHandler (like `self` in Python)
- `h` is the receiver (like `self`)
- Methods let you attach functions to structs

```go
    // Upgrade HTTP connection to WebSocket
    conn, err := h.upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Printf("Failed to upgrade connection: %v", err)
        return
    }
    defer conn.Close()
```
**Lines 47-52**: 
- Upgrade the HTTP request to a WebSocket connection
- Check for errors (`if err != nil` is Go's standard error handling)
- `defer conn.Close()` ensures the connection closes when function exits

```go
    // Generate unique session ID
    sessionID := uuid.New().String()
    log.Printf("New WebSocket connection: %s", sessionID)
```
**Lines 55-56**: 
- Generate a UUID for this session (like Python's `uuid.uuid4()`)
- `.String()` converts UUID to string format

```go
    // Initialize session in session manager
    if err := h.sessionManager.InitSession(sessionID); err != nil {
        log.Printf("Failed to initialize session: %v", err)
        return
    }
```
**Lines 59-62**: Initialize the session in Redis and notify the Python service.

```go
    // Create channels for communication between goroutines
    audioFromClient := make(chan []byte, 100)
    transcriptToClient := make(chan string, 10)
    audioToClient := make(chan []byte, 10)
    done := make(chan struct{})
```
**Lines 65-68**: 
- Create **channels** (thread-safe queues) for goroutine communication
- `make(chan []byte, 100)` creates a buffered channel that can hold 100 items
- Buffered channels don't block until full (like a queue with max size)
- `chan struct{}` is an empty channel used just for signaling (like a semaphore)

```go
    // WaitGroup to track goroutines
    var wg sync.WaitGroup
```
**Line 71**: 
- `sync.WaitGroup` tracks running goroutines (like thread pool)
- Used to wait for all goroutines to finish before exiting

```go
    // Start Deepgram STT (Speech-to-Text)
    wg.Add(1)
    go func() {
        defer wg.Done()
        stt := services.NewDeepgramSTT(h.deepgramAPIKey)
        if err := stt.StreamAudio(context.Background(), audioFromClient, transcriptToClient); err != nil {
            log.Printf("STT error: %v", err)
        }
    }()
```
**Lines 74-81**: 
- `wg.Add(1)` increments the wait group counter (one more goroutine to wait for)
- `go func() { ... }()` starts a goroutine (background thread)
- `defer wg.Done()` decrements the counter when goroutine exits
- This goroutine runs STT: reads from `audioFromClient`, writes to `transcriptToClient`

```go
    // Goroutine to read messages from client
    wg.Add(1)
    go func() {
        defer wg.Done()
        defer close(done) // Signal other goroutines to stop
        
        for {
            var msg Message
            if err := conn.ReadJSON(&msg); err != nil {
                log.Printf("Read error: %v", err)
                return
            }
```
**Lines 84-95**: 
- Start a goroutine to read WebSocket messages from the client
- `for { ... }` is an infinite loop (like `while True`)
- `conn.ReadJSON(&msg)` reads JSON and decodes into `msg` struct
- `&msg` passes a pointer so the function can modify `msg`

```go
            switch msg.Type {
            case "audio":
                // Decode base64 audio data
                audioData, err := base64.StdEncoding.DecodeString(msg.Data)
                if err != nil {
                    log.Printf("Failed to decode audio: %v", err)
                    continue
                }
                
                // Send to STT
                select {
                case audioFromClient <- audioData:
                default:
                    log.Println("Audio channel full, dropping frame")
                }
```
**Lines 97-110**: 
- `switch msg.Type` is like Python's `if/elif` (but more efficient)
- Decode base64 audio to binary
- `select` is like an `if` for channels (non-blocking send)
- `case audioFromClient <- audioData:` tries to send to the channel
- `default:` executes if the channel is full (drops the frame instead of blocking)

```go
            case "end_call":
                log.Printf("Call ended for session %s", sessionID)
                return // Exit goroutine, trigger cleanup
            }
        }
    }()
```
**Lines 112-116**: Handle "end_call" message by exiting the goroutine.

```go
    // Goroutine to send transcripts to client
    wg.Add(1)
    go func() {
        defer wg.Done()
        
        for {
            select {
            case transcript := <-transcriptToClient:
                // Send transcript to Python LLM service
                response, err := h.sessionManager.ProcessTranscript(sessionID, transcript)
                if err != nil {
                    log.Printf("Failed to process transcript: %v", err)
                    continue
                }
```
**Lines 119-131**: 
- Start a goroutine to handle transcripts from Deepgram
- `<-transcriptToClient` **receives** from the channel (blocks until data available)
- Send transcript to Python service for LLM processing

```go
                // Send transcript to client
                if err := conn.WriteJSON(Message{
                    Type:    "transcript",
                    Text:    transcript,
                    Speaker: "user",
                }); err != nil {
                    log.Printf("Failed to send transcript: %v", err)
                    return
                }
```
**Lines 134-141**: Send the user's transcript back to the client as JSON.

```go
                // Send AI response text to client
                if err := conn.WriteJSON(Message{
                    Type:    "transcript",
                    Text:    response,
                    Speaker: "ai",
                }); err != nil {
                    log.Printf("Failed to send AI response: %v", err)
                    return
                }
```
**Lines 144-151**: Send the AI's response text to the client.

```go
                // Generate TTS audio from AI response
                tts := services.NewDeepgramTTS(h.deepgramAPIKey)
                audioData, err := tts.Synthesize(context.Background(), response)
                if err != nil {
                    log.Printf("TTS error: %v", err)
                    continue
                }
```
**Lines 154-159**: 
- Create a TTS service
- Synthesize audio from the AI's text response
- Handle errors without crashing

```go
                // Send audio to client
                audioToClient <- audioData
```
**Line 162**: Send the audio data to the channel (to be sent to client).

```go
            case <-done:
                return
            }
        }
    }()
```
**Lines 164-167**: 
- `case <-done:` receives from the `done` channel
- When the client disconnects, `done` closes and this exits the goroutine

```go
    // Goroutine to send audio to client
    wg.Add(1)
    go func() {
        defer wg.Done()
        
        for {
            select {
            case audioData := <-audioToClient:
                // Encode audio as base64
                audioBase64 := base64.StdEncoding.EncodeToString(audioData)
                
                // Send to client
                if err := conn.WriteJSON(Message{
                    Type:       "audio",
                    Data:       audioBase64,
                    SampleRate: 16000,
                }); err != nil {
                    log.Printf("Failed to send audio: %v", err)
                    return
                }
```
**Lines 170-188**: 
- Start a goroutine to send AI audio to the client
- Read from `audioToClient` channel
- Encode binary audio as base64 (JSON-safe)
- Send as WebSocket message

```go
            case <-done:
                return
            }
        }
    }()
```
**Lines 190-193**: Exit when `done` closes.

```go
    // Wait for all goroutines to finish
    wg.Wait()
    
    log.Printf("WebSocket connection closed: %s", sessionID)
}
```
**Lines 196-199**: 
- `wg.Wait()` blocks until all `wg.Done()` calls happen
- Ensures all goroutines finish before function exits
- Logs the session end

---

## services/session_manager.go

**Purpose**: Coordinate between Redis state, Python LLM service, and WebSocket handler.

```go
// filepath: streaming-gateway/internal/services/session_manager.go
package services

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)
```
**Lines 1-10**: Standard imports for HTTP, JSON, and formatting.

```go
// SessionManager manages session state and coordinates with Python LLM service
type SessionManager struct {
    redis       *RedisClient
    llmURL      string
    httpClient  *http.Client
}
```
**Lines 12-17**: 
- Struct to manage sessions
- Holds Redis client, Python service URL, and HTTP client

```go
// NewSessionManager creates a new session manager
func NewSessionManager(redis *RedisClient, llmURL string) *SessionManager {
    return &SessionManager{
        redis:  redis,
        llmURL: llmURL,
        httpClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}
```
**Lines 19-28**: 
- Constructor
- Creates HTTP client with 30-second timeout (prevents hanging forever)

```go
// InitSession initializes a new session
func (sm *SessionManager) InitSession(sessionID string) error {
    // Store session in Redis
    sessionData := map[string]interface{}{
        "created_at":      time.Now().Unix(),
        "current_section": "GREETING",
        "collected_fields": map[string]interface{}{},
    }
```
**Lines 30-37**: 
- Method to initialize a session
- `map[string]interface{}` is a dictionary where keys are strings and values can be anything
- `interface{}` is Go's "any type" (like `object` in Java or `Any` in TypeScript)

```go
    jsonData, err := json.Marshal(sessionData)
    if err != nil {
        return fmt.Errorf("failed to marshal session data: %w", err)
    }
```
**Lines 39-42**: 
- `json.Marshal` converts the map to JSON bytes (like `json.dumps()`)
- `%w` wraps the error (adds context while preserving the original error)

```go
    return sm.redis.Set(fmt.Sprintf("session:%s", sessionID), string(jsonData), 24*time.Hour)
}
```
**Line 44**: 
- Store in Redis with key `session:<uuid>`
- Expires after 24 hours
- `fmt.Sprintf` is like Python's f-strings

```go
// ProcessTranscript sends transcript to Python LLM service and returns AI response
func (sm *SessionManager) ProcessTranscript(sessionID, transcript string) (string, error) {
    // Prepare request payload
    payload := map[string]string{
        "session_id": sessionID,
        "user_input": transcript,
    }
```
**Lines 47-52**: 
- Method to send transcript to Python service
- Returns two values: `string` (response) and `error` (Go's way of error handling)
- Create request payload as a map

```go
    jsonPayload, err := json.Marshal(payload)
    if err != nil {
        return "", fmt.Errorf("failed to marshal payload: %w", err)
    }
```
**Lines 54-57**: Convert payload to JSON.

```go
    // Send HTTP POST request to Python service
    resp, err := sm.httpClient.Post(
        fmt.Sprintf("%s/generate", sm.llmURL),
        "application/json",
        bytes.NewBuffer(jsonPayload),
    )
    if err != nil {
        return "", fmt.Errorf("failed to call LLM service: %w", err)
    }
    defer resp.Body.Close()
```
**Lines 60-68**: 
- Make HTTP POST request to Python service
- `bytes.NewBuffer` wraps the JSON bytes in a Reader (Go's HTTP needs a Reader interface)
- `defer resp.Body.Close()` ensures we close the response body (prevents memory leaks)

```go
    // Check response status
    if resp.StatusCode != http.StatusOK {
        return "", fmt.Errorf("LLM service returned status %d", resp.StatusCode)
    }
```
**Lines 71-73**: Check if HTTP status is 200 OK.

```go
    // Decode response
    var result struct {
        Response string `json:"response"`
    }
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return "", fmt.Errorf("failed to decode response: %w", err)
    }
```
**Lines 76-81**: 
- Define an anonymous struct inline (just for this response)
- `json.NewDecoder` reads JSON from the response body
- `.Decode(&result)` parses JSON into the struct

```go
    return result.Response, nil
}
```
**Line 83**: 
- Return the AI response and `nil` error (meaning no error)
- In Go, functions return errors explicitly (no exceptions)

---

## services/redis.go

**Purpose**: Wrapper around Redis client for session state.

```go
// filepath: streaming-gateway/internal/services/redis.go
package services

import (
    "context"
    "time"

    "github.com/go-redis/redis/v8"
)
```
**Lines 1-9**: Standard imports plus the Redis library.

```go
// RedisClient wraps the Redis client
type RedisClient struct {
    client *redis.Client
}
```
**Lines 11-14**: 
- Wrapper struct around the Redis client
- We wrap it so we can add custom methods and hide implementation details

```go
// NewRedisClient creates a new Redis client
func NewRedisClient(url string) *RedisClient {
    opt, err := redis.ParseURL(url)
    if err != nil {
        panic(err) // In production, handle this more gracefully
    }
```
**Lines 16-21**: 
- Parse Redis URL (e.g., `redis://localhost:6379/0`)
- `panic(err)` crashes the program (like `raise` in Python)
- We panic here because without Redis, the app can't work

```go
    client := redis.NewClient(opt)
    
    return &RedisClient{
        client: client,
    }
}
```
**Lines 23-27**: Create Redis client and wrap it in our struct.

```go
// Set stores a value in Redis with expiration
func (rc *RedisClient) Set(key, value string, expiration time.Duration) error {
    ctx := context.Background()
    return rc.client.Set(ctx, key, value, expiration).Err()
}
```
**Lines 29-33**: 
- Method to set a key-value pair in Redis
- `context.Background()` creates a basic context (required by Redis library)
- `time.Duration` is Go's type for time periods (like `24*time.Hour`)
- `.Err()` extracts the error from the Redis result

```go
// Get retrieves a value from Redis
func (rc *RedisClient) Get(key string) (string, error) {
    ctx := context.Background()
    return rc.client.Get(ctx, key).Result()
}
```
**Lines 35-39**: 
- Method to get a value from Redis
- Returns both the value and an error (Go pattern)
- If key doesn't exist, error will be `redis.Nil`

```go
// Delete removes a key from Redis
func (rc *RedisClient) Delete(key string) error {
    ctx := context.Background()
    return rc.client.Del(ctx, key).Err()
}
```
**Lines 41-45**: Method to delete a key.

```go
// Close closes the Redis connection
func (rc *RedisClient) Close() error {
    return rc.client.Close()
}
```
**Lines 47-50**: Method to close the connection (called by `defer` in main).

---

## services/deepgram_stt.go

**Purpose**: Stream audio to Deepgram for real-time speech-to-text.

```go
// filepath: streaming-gateway/internal/services/deepgram_stt.go
package services

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "net/url"

    "github.com/gorilla/websocket"
    "go.uber.org/zap"
)
```
**Lines 1-13**: 
- Standard imports
- `gorilla/websocket`: WebSocket client library
- `go.uber.org/zap`: Fast structured logging library

```go
// DeepgramSTT handles speech-to-text via Deepgram
type DeepgramSTT struct {
    apiKey string
    logger *zap.Logger
}
```
**Lines 15-19**: Struct to hold Deepgram API key and logger.

```go
// NewDeepgramSTT creates a new STT service
func NewDeepgramSTT(apiKey string) *DeepgramSTT {
    logger, _ := zap.NewProduction()
    return &DeepgramSTT{
        apiKey: apiKey,
        logger: logger,
    }
}
```
**Lines 21-27**: 
- Constructor
- `zap.NewProduction()` creates a production logger (JSON structured logs)

```go
// StreamAudio streams audio to Deepgram and returns transcripts
func (stt *DeepgramSTT) StreamAudio(ctx context.Context, audioInput <-chan []byte, transcriptOutput chan<- string) error {
```
**Lines 29-30**: 
- Method signature with special channel types:
- `<-chan []byte` is a **receive-only** channel (can only read from it)
- `chan<- string` is a **send-only** channel (can only write to it)
- This prevents accidental misuse (compile-time safety)

```go
    // Build Deepgram WebSocket URL
    u, err := url.Parse("wss://api.deepgram.com/v1/listen")
    if err != nil {
        return fmt.Errorf("failed to parse URL: %w", err)
    }
```
**Lines 32-36**: Parse the Deepgram WebSocket URL.

```go
    // Add query parameters
    q := u.Query()
    q.Set("encoding", "linear16")
    q.Set("sample_rate", "16000")
    q.Set("channels", "1")
    q.Set("language", "en-US")
    q.Set("model", "nova-2")
    u.RawQuery = q.Encode()
```
**Lines 39-45**: 
- Build query parameters for Deepgram API
- `linear16`: PCM audio format
- `16000`: 16kHz sample rate
- `nova-2`: Deepgram's latest model

```go
    // Set up WebSocket headers with API key
    headers := map[string][]string{
        "Authorization": {fmt.Sprintf("Token %s", stt.apiKey)},
    }
```
**Lines 48-50**: 
- HTTP headers for WebSocket connection
- `map[string][]string` because headers can have multiple values

```go
    // Connect to Deepgram
    conn, _, err := websocket.DefaultDialer.Dial(u.String(), headers)
    if err != nil {
        return fmt.Errorf("failed to connect to Deepgram: %w", err)
    }
    defer conn.Close()
```
**Lines 53-58**: 
- Connect to Deepgram WebSocket
- `websocket.DefaultDialer.Dial` is like `websocket.connect()` in Python
- The second return value (blank `_`) is the HTTP response (we don't need it)

```go
    log.Println("Connected to Deepgram STT")
```
**Line 60**: Log successful connection.

```go
    // Channel to signal when to stop
    done := make(chan struct{})
```
**Line 63**: Create a signaling channel.

```go
    // Goroutine to read transcripts from Deepgram
    go func() {
        defer close(done)
        for {
            _, message, err := conn.ReadMessage()
            if err != nil {
                log.Printf("Deepgram read error: %v", err)
                return
            }
```
**Lines 66-74**: 
- Start goroutine to read from Deepgram
- `conn.ReadMessage()` blocks until a message arrives
- Returns message type (we ignore it), message bytes, and error

```go
            // Parse Deepgram response
            var response struct {
                Channel struct {
                    Alternatives []struct {
                        Transcript string `json:"transcript"`
                    } `json:"alternatives"`
                } `json:"channel"`
            }
```
**Lines 77-84**: 
- Define struct matching Deepgram's JSON response format
- Nested structs for nested JSON
- This is Go's way of parsing JSON (type-safe)

```go
            if err := json.Unmarshal(message, &response); err != nil {
                log.Printf("Failed to parse Deepgram response: %v", err)
                continue
            }
```
**Lines 86-89**: 
- `json.Unmarshal` parses JSON bytes into the struct
- Continue on error (don't crash)

```go
            // Extract transcript
            if len(response.Channel.Alternatives) > 0 {
                transcript := response.Channel.Alternatives[0].Transcript
                if transcript != "" {
                    select {
                    case transcriptOutput <- transcript:
                    case <-ctx.Done():
                        return
                    }
                }
            }
        }
    }()
```
**Lines 92-103**: 
- Check if there are alternatives (Deepgram can return multiple)
- Get the first transcript
- Use `select` to send transcript OR exit if context is cancelled
- `ctx.Done()` returns a channel that closes when context is cancelled

```go
    // Send audio to Deepgram
    for {
        select {
        case audioData := <-audioInput:
            if err := conn.WriteMessage(websocket.BinaryMessage, audioData); err != nil {
                return fmt.Errorf("failed to send audio: %w", err)
            }
```
**Lines 106-111**: 
- Main loop: read audio from input channel
- Send to Deepgram as binary WebSocket message
- `websocket.BinaryMessage` specifies binary (not text)

```go
        case <-done:
            return nil
        case <-ctx.Done():
            return ctx.Err()
        }
    }
}
```
**Lines 113-118**: 
- Exit if `done` closes (reading goroutine stopped)
- Exit if context is cancelled
- Return context error (will be `context.Canceled` or `context.DeadlineExceeded`)

---

## services/deepgram_tts.go

**Purpose**: Synthesize speech from text using Deepgram.

```go
// filepath: streaming-gateway/internal/services/deepgram_tts.go
package services

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)
```
**Lines 1-12**: Standard imports for HTTP and JSON.

```go
// DeepgramTTS handles text-to-speech via Deepgram
type DeepgramTTS struct {
    apiKey     string
    httpClient *http.Client
}
```
**Lines 14-18**: Struct for TTS service.

```go
// NewDeepgramTTS creates a new TTS service
func NewDeepgramTTS(apiKey string) *DeepgramTTS {
    return &DeepgramTTS{
        apiKey: apiKey,
        httpClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}
```
**Lines 20-28**: Constructor with 30-second timeout.

```go
// Synthesize converts text to speech
func (tts *DeepgramTTS) Synthesize(ctx context.Context, text string) ([]byte, error) {
    // Prepare request payload
    payload := map[string]interface{}{
        "text": text,
    }
```
**Lines 30-35**: 
- Method to synthesize speech
- Takes context for cancellation
- Returns audio bytes and error

```go
    jsonPayload, err := json.Marshal(payload)
    if err != nil {
        return nil, fmt.Errorf("failed to marshal payload: %w", err)
    }
```
**Lines 37-40**: Convert payload to JSON.

```go
    // Create HTTP request
    req, err := http.NewRequestWithContext(
        ctx,
        "POST",
        "https://api.deepgram.com/v1/speak?model=aura-asteria-en",
        bytes.NewBuffer(jsonPayload),
    )
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
```
**Lines 43-51**: 
- `http.NewRequestWithContext` creates request with cancellation support
- `aura-asteria-en` is Deepgram's voice model
- POST request with JSON body

```go
    // Set headers
    req.Header.Set("Authorization", fmt.Sprintf("Token %s", tts.apiKey))
    req.Header.Set("Content-Type", "application/json")
```
**Lines 54-55**: Set authentication and content type headers.

```go
    // Send request
    resp, err := tts.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to call Deepgram TTS: %w", err)
    }
    defer resp.Body.Close()
```
**Lines 58-63**: 
- Execute HTTP request
- `defer resp.Body.Close()` ensures we close the response

```go
    // Check status code
    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("Deepgram TTS returned status %d: %s", resp.StatusCode, string(body))
    }
```
**Lines 66-69**: 
- Check for success status
- Read error body for debugging
- `io.ReadAll` reads all bytes from the response

```go
    // Read audio data
    audioData, err := io.ReadAll(resp.Body)
    if err != nil {
        return nil, fmt.Errorf("failed to read audio data: %w", err)
    }
```
**Lines 72-75**: Read the audio bytes from response.

```go
    return audioData, nil
}
```
**Line 77**: Return audio data and no error.

---

## services/llm_client.go

**Purpose**: HTTP client to call the Python LLM service (currently handled in session_manager.go, but could be extracted here for better organization).

This file could be created to separate HTTP concerns:

````go
// filepath: streaming-gateway/internal/services/llm_client.go
package services

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

// LLMClient handles communication with the Python LLM service
type LLMClient struct {
    baseURL    string
    httpClient *http.Client
}

// NewLLMClient creates a new LLM client
func NewLLMClient(baseURL string) *LLMClient {
    return &LLMClient{
        baseURL: baseURL,
        httpClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

// GenerateResponse calls the Python LLM service to generate a response
func (c *LLMClient) GenerateResponse(ctx context.Context, sessionID, userInput string) (string, error) {
    // Prepare request
    payload := map[string]string{
        "session_id": sessionID,
        "user_input": userInput,
    }
    
    jsonPayload, err := json.Marshal(payload)
    if err != nil {
        return "", fmt.Errorf("marshal payload: %w", err)
    }
    
    // Create request with context
    req, err := http.NewRequestWithContext(
        ctx,
        "POST",
        fmt.Sprintf("%s/generate", c.baseURL),
        bytes.NewBuffer(jsonPayload),
    )
    if err != nil {
        return "", fmt.Errorf("create request: %w", err)
    }
    
    req.Header.Set("Content-Type", "application/json")
    
    // Execute request
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return "", fmt.Errorf("execute request: %w", err)
    }
    defer resp.Body.Close()
    
    // Check status
    if resp.StatusCode != http.StatusOK {
        return "", fmt.Errorf("unexpected status: %d", resp.StatusCode)
    }
    
    // Parse response
    var result struct {
        Response string `json:"response"`
    }
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return "", fmt.Errorf("decode response: %w", err)
    }
    
    return result.Response, nil
}
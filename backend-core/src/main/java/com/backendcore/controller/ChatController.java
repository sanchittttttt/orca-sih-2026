package com.backendcore.controller;

import com.backendcore.model.ChatMessage;
import com.backendcore.model.ChatSession;
import com.backendcore.repository.ChatMessageRepository;
import com.backendcore.repository.ChatSessionRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * No auth — this is a prototype. Sessions are identified by a plain UUID the
 * frontend keeps track of (or omits, to start a new one each time).
 */
@RestController
@CrossOrigin(
        origins = {
                "http://localhost:8001",
                "http://127.0.0.1:8001",
                "http://localhost:8000",
                "http://127.0.0.1:8000"
        },
        methods = {RequestMethod.GET, RequestMethod.POST, RequestMethod.OPTIONS},
        allowedHeaders = {"*"}
)
@RequestMapping("/api")
public class ChatController {

    @Value("${orca.ai-service.url}")
    private String aiServiceUrl;

    @Autowired
    private ChatSessionRepository sessionRepository;

    @Autowired
    private ChatMessageRepository messageRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private final RestTemplate restTemplate = new RestTemplate(clientHttpRequestFactory());

    private static SimpleClientHttpRequestFactory clientHttpRequestFactory() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);
        factory.setReadTimeout(90_000);
        return factory;
    }

    @PostMapping("/chat")
    public ResponseEntity<Map<String, Object>> chat(@RequestBody Map<String, Object> request) {
        // Resolve or create a session
        boolean isNewSession = request.get("sessionId") == null;
        UUID sessionId;
        if (!isNewSession) {
            sessionId = UUID.fromString(request.get("sessionId").toString());
        } else {
            ChatSession newSession = new ChatSession();
            sessionRepository.save(newSession);
            sessionId = newSession.getId();
        }

        // Fetch prior history BEFORE persisting the new user message, so the
        // AI service gets everything that happened before this turn, not
        // including it.
        List<Map<String, String>> history = new ArrayList<>();
        if (!isNewSession) {
            List<ChatMessage> priorMessages = messageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
            for (ChatMessage m : priorMessages) {
                String content = m.getContent();
                // Assistant messages are stored as full JSON - extract just the
                // plain explanation text so the AI service gets clean context,
                // not a wall of nested JSON to parse.
                if ("assistant".equals(m.getRole())) {
                    try {
                        JsonNode node = objectMapper.readTree(content);
                        if (node.has("explanation_text")) {
                            content = node.get("explanation_text").asText();
                        }
                    } catch (Exception ignored) {
                        // fall back to raw content if it's not valid JSON for some reason
                    }
                }
                Map<String, String> entry = new HashMap<>();
                entry.put("role", m.getRole());
                entry.put("content", content);
                history.add(entry);
            }
        }

        // Persist the user's message
        ChatMessage userMessage = new ChatMessage();
        userMessage.setSessionId(sessionId);
        userMessage.setRole("user");
        userMessage.setContent(request.get("query").toString());
        messageRepository.save(userMessage);

        // Build the request to the AI service, including history
        Map<String, Object> aiRequest = new HashMap<>(request);
        aiRequest.put("history", history);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(aiRequest, headers);

        ResponseEntity<Map> aiResponse = restTemplate.postForEntity(
                aiServiceUrl + "/ai/agent/run",
                entity,
                Map.class
        );

        Map responseBody = aiResponse.getBody();

        // Persist the assistant's response (serialized as JSON text)
        ChatMessage assistantMessage = new ChatMessage();
        assistantMessage.setSessionId(sessionId);
        assistantMessage.setRole("assistant");
        try {
            assistantMessage.setContent(objectMapper.writeValueAsString(responseBody));
        } catch (Exception e) {
            assistantMessage.setContent(String.valueOf(responseBody));
        }
        messageRepository.save(assistantMessage);

        // Return the AI response plus the sessionId so the frontend can continue the conversation
        Map<String, Object> result = new HashMap<>(responseBody);
        result.put("sessionId", sessionId.toString());

        return ResponseEntity.ok(result);
    }

    @GetMapping("/conversations/{sessionId}")
    public List<Map<String, Object>> getConversation(@PathVariable String sessionId) {
        UUID id = UUID.fromString(sessionId);
        return messageRepository.findBySessionIdOrderByCreatedAtAsc(id).stream()
                .map(m -> Map.<String, Object>of(
                        "role", m.getRole(),
                        "content", m.getContent(),
                        "createdAt", m.getCreatedAt().toString()
                ))
                .collect(Collectors.toList());
    }

    /**
     * Lists all past sessions, newest first, with a short preview (the first
     * user message of each) — this is what powers a "reload past
     * conversation" screen on the frontend.
     */
    @GetMapping("/sessions")
    public List<Map<String, Object>> listSessions() {
        return sessionRepository.findAll().stream()
                .sorted(Comparator.comparing(ChatSession::getCreatedAt).reversed())
                .map(s -> {
                    String preview = messageRepository.findFirstBySessionIdOrderByCreatedAtAsc(s.getId())
                            .map(ChatMessage::getContent)
                            .orElse("(empty conversation)");
                    return Map.<String, Object>of(
                            "sessionId", s.getId().toString(),
                            "createdAt", s.getCreatedAt().toString(),
                            "preview", preview
                    );
                })
                .collect(Collectors.toList());
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
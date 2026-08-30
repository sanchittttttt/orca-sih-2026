package com.backendcore;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * Minimal working version — no auth, no database yet. Just forwards the
 * request to the AI Agent Service and returns whatever it says. This is
 * "synchronous": the method waits for the AI service to respond before
 * returning anything to the frontend.
 */
@RestController
@RequestMapping("/api")
public class ChatController {

    @Value("${orca.ai-service.url}")
    private String aiServiceUrl;

    // The AI service can take up to a minute on free-tier LLM calls, so we
    // need a generous read timeout or Spring will give up early.
    private final RestTemplate restTemplate = new RestTemplate(clientHttpRequestFactory());

    private static SimpleClientHttpRequestFactory clientHttpRequestFactory() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);   // 10 seconds to establish connection
        factory.setReadTimeout(90_000);      // 90 seconds to wait for the full response
        return factory;
    }

    @PostMapping("/chat")
    public ResponseEntity<Map> chat(@RequestBody Map<String, Object> request) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(
                aiServiceUrl + "/ai/agent/run",
                entity,
                Map.class
        );

        return ResponseEntity.ok(response.getBody());
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
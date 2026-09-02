package com.backendcore.repository;

import com.backendcore.model.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, UUID> {
    List<ChatMessage> findBySessionIdOrderByCreatedAtAsc(UUID sessionId);

    // Used to build a short "preview" of each conversation for the sessions list
    Optional<ChatMessage> findFirstBySessionIdOrderByCreatedAtAsc(UUID sessionId);
}
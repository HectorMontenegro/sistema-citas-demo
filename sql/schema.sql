CREATE TABLE IF NOT EXISTS appointment_requests (
    id CHAR(36) PRIMARY KEY,
    contact_email VARCHAR(254) NOT NULL,
    preferred_from DATE NOT NULL,
    preferred_to DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    attempts SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
    selected_date DATE NULL,
    selected_time TIME NULL,
    confirmation_code VARCHAR(64) NULL,
    last_error VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_request_dates CHECK (preferred_to >= preferred_from),
    CONSTRAINT chk_request_status CHECK (
        status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')
    ),
    INDEX idx_request_queue (status, created_at),
    INDEX idx_request_email (contact_email)
);

CREATE TABLE IF NOT EXISTS request_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_id CHAR(36) NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    detail VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_event_request
        FOREIGN KEY (request_id)
        REFERENCES appointment_requests(id)
        ON DELETE CASCADE,
    INDEX idx_event_request_time (request_id, created_at)
);

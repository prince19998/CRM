CREATE DATABASE IF NOT EXISTS ai_crm
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ai_crm;

CREATE TABLE IF NOT EXISTS leads (
    id          INT            NOT NULL AUTO_INCREMENT,
    name        VARCHAR(150)   NOT NULL,
    email       VARCHAR(255)   NOT NULL,
    company     VARCHAR(200)   NOT NULL DEFAULT '',
    lead_source VARCHAR(100)   NOT NULL DEFAULT 'Website',
    status      VARCHAR(50)    NOT NULL DEFAULT 'New',
    notes       TEXT           NULL,
    created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    -- Unique email (case-insensitive under utf8mb4_unicode_ci); also the lookup index.
    UNIQUE KEY uq_leads_email (email),
    KEY idx_leads_status (status),
    KEY idx_leads_lead_source (lead_source),
    KEY idx_leads_name (name),
    KEY idx_leads_company (company),
    KEY idx_leads_created_at (created_at),
    CONSTRAINT chk_leads_status
        CHECK (status IN ('New', 'Contacted', 'Interested', 'Converted', 'Lost'))
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

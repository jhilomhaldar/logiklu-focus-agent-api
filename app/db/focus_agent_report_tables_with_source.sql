CREATE TABLE IF NOT EXISTS `lk_focus_agent_report_master` (
    `agent_report_id` BIGINT(19) NOT NULL AUTO_INCREMENT,
    `report_slot` ENUM('current') NOT NULL DEFAULT 'current',
    `source_report_id` BIGINT(19) NOT NULL,
    `report_uid` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_unicode_ci',
    `report_batch_uid` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_unicode_ci',
    `executive_snapshot_json` JSON NULL DEFAULT NULL,
    `buyer_intent_snapshot_json` JSON NULL DEFAULT NULL,
    `priority_account_count` INT(10) NOT NULL DEFAULT 0,
    `interacted_contact_count` INT(10) NOT NULL DEFAULT 0,
    `raw_payload_json` JSON NULL DEFAULT NULL,
    `created_date` DATETIME NOT NULL,
    `updated_date` DATETIME NULL DEFAULT NULL,
    PRIMARY KEY (`agent_report_id`) USING BTREE,
    UNIQUE KEY `uniq_report_slot` (`report_slot`) USING BTREE,
    INDEX `idx_source_report_id` (`source_report_id`) USING BTREE,
    INDEX `idx_report_uid` (`report_uid`) USING BTREE,
    INDEX `idx_batch_uid` (`report_batch_uid`) USING BTREE
)
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS `lk_focus_agent_report_priority_account` (
    `agent_report_account_id` BIGINT(19) NOT NULL AUTO_INCREMENT,
    `agent_report_id` BIGINT(19) NOT NULL,
    `source_report_id` BIGINT(19) NOT NULL,
    `report_uid` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_unicode_ci',
    `report_batch_uid` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_unicode_ci',
    `account_id` BIGINT(19) NOT NULL,
    `source_company_log_id` BIGINT(19) NULL DEFAULT NULL,
    `source_type` VARCHAR(100) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `source_summary` TEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `source_json` JSON NULL DEFAULT NULL,
    `priority_rank` INT(10) NULL DEFAULT NULL,
    `account_name` VARCHAR(255) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `website` VARCHAR(255) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `country` VARCHAR(255) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `state` VARCHAR(255) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `city` VARCHAR(255) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `final_explanation_json` JSON NULL DEFAULT NULL,
    `engagement_pattern_json` JSON NULL DEFAULT NULL,
    `why_company_matters_json` JSON NULL DEFAULT NULL,
    `account_insight_summary` TEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `account_snapshot_json` JSON NULL DEFAULT NULL,
    `created_date` DATETIME NOT NULL,
    PRIMARY KEY (`agent_report_account_id`) USING BTREE,
    UNIQUE KEY `uniq_agent_report_account` (`agent_report_id`, `account_id`) USING BTREE,
    INDEX `idx_agent_report_id` (`agent_report_id`) USING BTREE,
    INDEX `idx_source_report_id` (`source_report_id`) USING BTREE,
    INDEX `idx_account_id` (`account_id`) USING BTREE,
    INDEX `idx_source_company_log_id` (`source_company_log_id`) USING BTREE,
    INDEX `idx_priority_rank` (`agent_report_id`, `priority_rank`) USING BTREE
)
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS `lk_focus_agent_report_contact_interaction` (
    `agent_report_contact_id` BIGINT(19) NOT NULL AUTO_INCREMENT,
    `agent_report_id` BIGINT(19) NOT NULL,
    `source_report_id` BIGINT(19) NOT NULL,
    `report_uid` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_unicode_ci',
    `report_batch_uid` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_unicode_ci',
    `account_id` BIGINT(19) NOT NULL,
    `contact_id` BIGINT(19) NULL DEFAULT NULL,
    `contact_name` VARCHAR(255) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `contact_email` VARCHAR(255) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `contact_phone` VARCHAR(100) NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `interaction_details_json` JSON NULL DEFAULT NULL,
    `interaction_summary` TEXT NULL DEFAULT NULL COLLATE 'utf8mb4_unicode_ci',
    `contact_snapshot_json` JSON NULL DEFAULT NULL,
    `created_date` DATETIME NOT NULL,
    PRIMARY KEY (`agent_report_contact_id`) USING BTREE,
    INDEX `idx_agent_report_id` (`agent_report_id`) USING BTREE,
    INDEX `idx_source_report_id` (`source_report_id`) USING BTREE,
    INDEX `idx_account_id` (`account_id`) USING BTREE,
    INDEX `idx_contact_id` (`contact_id`) USING BTREE,
    INDEX `idx_account_contact` (`account_id`, `contact_id`) USING BTREE
)
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB;

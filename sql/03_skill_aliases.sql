USE orbit_jr;

CREATE TABLE IF NOT EXISTS skill_aliases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    skill_id INT NOT NULL,
    alias VARCHAR(255) NOT NULL,
    normalized_alias VARCHAR(255) NOT NULL,
    source VARCHAR(50) DEFAULT 'esco',

    FOREIGN KEY (skill_id)
        REFERENCES skills(id)
        ON DELETE CASCADE,

    UNIQUE (skill_id, normalized_alias),
    INDEX idx_skill_alias_normalized (normalized_alias)
);
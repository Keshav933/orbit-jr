USE orbit_jr;


ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS seniority_level VARCHAR(100),
ADD COLUMN IF NOT EXISTS employment_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS job_function VARCHAR(150),
ADD COLUMN IF NOT EXISTS industry VARCHAR(200),
ADD COLUMN IF NOT EXISTS role_family_hint VARCHAR(150),
ADD COLUMN IF NOT EXISTS domain_hint VARCHAR(150),
ADD COLUMN IF NOT EXISTS scraped_at DATETIME;


ALTER TABLE jobs
ADD INDEX idx_jobs_location (location),
ADD INDEX idx_jobs_role_family (role_family_hint),
ADD INDEX idx_jobs_remote (is_remote),
ADD INDEX idx_jobs_posted_date (posted_date);


ALTER TABLE jobs
ADD FULLTEXT INDEX ft_jobs_search (title, description);
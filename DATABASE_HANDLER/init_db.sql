CREATE TABLE IF NOT EXISTS ADMIN_USERS (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS blogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE,
    blog JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    type VARCHAR(50) NOT NULL DEFAULT 'BLOG',
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    keyword JSONB,
    editors_choice VARCHAR(1) DEFAULT 'N',
    redirect_url TEXT,
    isDeleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_blogs_status ON blogs(status) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_blogs_type ON blogs(type) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_blogs_date ON blogs(date DESC) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_blogs_slug ON blogs(slug) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_blogs_isDeleted ON blogs(isDeleted);
CREATE INDEX IF NOT EXISTS idx_blogs_keyword ON blogs USING GIN(keyword);
CREATE INDEX IF NOT EXISTS idx_blogs_blog ON blogs USING GIN(blog);

CREATE TABLE IF NOT EXISTS case_studies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE,
    blog JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    type VARCHAR(50) NOT NULL DEFAULT 'CASE STUDY',
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    keyword JSONB,
    preview JSONB,
    editors_choice VARCHAR(1) DEFAULT 'N',
    redirect_url TEXT,
    isDeleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_case_studies_status ON case_studies(status) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_case_studies_type ON case_studies(type) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_case_studies_date ON case_studies(date DESC) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_case_studies_slug ON case_studies(slug) WHERE isDeleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_case_studies_isDeleted ON case_studies(isDeleted);
CREATE INDEX IF NOT EXISTS idx_case_studies_keyword ON case_studies USING GIN(keyword);
CREATE INDEX IF NOT EXISTS idx_case_studies_preview ON case_studies USING GIN(preview);
CREATE INDEX IF NOT EXISTS idx_case_studies_blog ON case_studies USING GIN(blog);

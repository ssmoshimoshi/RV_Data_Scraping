-- ============================================================================
-- RUANG VISUAL — MARKET INTELLIGENCE RELATIONAL DATABASE SCHEMA
-- Target Engine: PostgreSQL 15+ / Supabase
-- Referensi: PRD_RUANG_VISUAL_MARKET_INTELLIGENCE.md Bab 6
-- ============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 2. ENUMS
DO $$ BEGIN
    CREATE TYPE platform_type AS ENUM (
        'instagram', 
        'google_maps', 
        'tiktok', 
        'facebook_ads', 
        'facebook_marketplace', 
        'threads', 
        'shopee_food', 
        'go_food', 
        'grab_food'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE business_category_type AS ENUM (
        'fnb_beverage',
        'fnb_food_resto',
        'fashion_retail',
        'beauty_skincare',
        'corporate_legal',
        'event_service',
        'new_store_opening',
        'general_commercial'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE outreach_status_type AS ENUM (
        'new_lead',
        'ready_to_pitch',
        'contacted',
        'sample_box_requested',
        'sample_box_dispatched',
        'sample_delivered',
        'quotation_sent',
        'negotiation',
        'won_deal',
        'lost_declined',
        'unresponsive',
        'blacklisted'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE scraper_engine_type AS ENUM (
        'in_house_crawlee',
        'in_house_direct_api',
        'apify_cloud_actor'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. TRIGGER FUNCTION: AUTO UPDATE TIMESTAMP
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. TABLE: target_sources
-- Menyimpan daftar sumber kampanye (misal: "Pengikut @bazar_makassar", "Resto Baru Panakkukang")
CREATE TABLE IF NOT EXISTS target_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name VARCHAR(255) NOT NULL,
    platform platform_type NOT NULL,
    target_handle_or_query VARCHAR(255) NOT NULL,
    target_type VARCHAR(100) NOT NULL, -- 'followers', 'following', 'hashtag', 'radius_geo', 'ad_archive'
    engine_used scraper_engine_type DEFAULT 'in_house_crawlee',
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    total_raw_found INTEGER DEFAULT 0,
    total_qualified_leads INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. TABLE: leads
-- Entitas inti calon pelanggan B2B RUANG VISUAL
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES target_sources(id) ON DELETE SET NULL,
    business_name VARCHAR(255) NOT NULL,
    category business_category_type NOT NULL DEFAULT 'general_commercial',
    platform platform_type NOT NULL,
    platform_profile_url TEXT,
    platform_handle VARCHAR(150),
    platform_id VARCHAR(150),
    
    -- Validasi Kontak
    whatsapp_number VARCHAR(30), -- Format bersih: 628xxxxxxxxxx
    phone_office VARCHAR(50),
    email_address VARCHAR(150),
    
    -- Lokasi & Alamat Fisik (Krusial untuk Pengiriman Sampel Bahan)
    address_full TEXT,
    district_area VARCHAR(100),
    city VARCHAR(100) DEFAULT 'Makassar',
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    google_maps_place_id VARCHAR(255),
    
    -- Metrik Aktivitas & Keaktifan (Anti-Blind Scraping Guard)
    follower_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    latest_post_date TIMESTAMP WITH TIME ZONE,
    is_active_verified BOOLEAN DEFAULT FALSE,
    is_ad_active BOOLEAN DEFAULT FALSE,
    external_website_url TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. TABLE: lead_insights
-- Mesin penalar kebutuhan cetak dan nilai intelijen bisnis
CREATE TABLE IF NOT EXISTS lead_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID UNIQUE REFERENCES leads(id) ON DELETE CASCADE,
    lead_score INTEGER NOT NULL CHECK (lead_score >= 0 AND lead_score <= 100),
    projected_products TEXT[] NOT NULL DEFAULT '{}',
    matched_keywords TEXT[] DEFAULT '{}',
    custom_pitch_hook TEXT,
    competitor_reference TEXT,
    qualification_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. TABLE: crm_outreach
-- Pelacak eksekusi tim sales, alur negosiasi, dan pengiriman sampel fisik
CREATE TABLE IF NOT EXISTS crm_outreach (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID UNIQUE REFERENCES leads(id) ON DELETE CASCADE,
    status outreach_status_type NOT NULL DEFAULT 'new_lead',
    
    -- Sample Box Physical Touchpoint
    sample_box_requested BOOLEAN DEFAULT FALSE,
    sample_box_type VARCHAR(100),
    sample_box_tracking_number VARCHAR(100),
    sample_box_courier VARCHAR(50),
    sample_delivered_at TIMESTAMP WITH TIME ZONE,
    
    -- Penawaran & Transaksi
    quotation_number VARCHAR(100),
    quotation_value NUMERIC(14, 2) DEFAULT 0,
    won_deal_value NUMERIC(14, 2) DEFAULT 0,
    projected_repeat_order_days INTEGER,
    next_follow_up_date DATE,
    
    -- Riwayat Interaksi
    interaction_history JSONB DEFAULT '[]'::jsonb,
    sales_agent_assigned VARCHAR(100),
    last_contacted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. TABLE: competitor_matrix
-- Analisis kelemahan percetakan pesaing untuk penetrasi pasar
CREATE TABLE IF NOT EXISTS competitor_matrix (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES target_sources(id) ON DELETE SET NULL,
    competitor_name VARCHAR(255) NOT NULL,
    google_maps_place_id VARCHAR(255),
    average_rating NUMERIC(3, 2),
    total_reviews INTEGER DEFAULT 0,
    extracted_weaknesses TEXT[] DEFAULT '{}',
    pricing_notes TEXT,
    ruang_visual_counter_pitch TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. TRIGGERS UNTUK AUTO-UPDATE TIMESTAMP
DROP TRIGGER IF EXISTS update_target_sources_timestamp ON target_sources;
CREATE TRIGGER update_target_sources_timestamp BEFORE UPDATE ON target_sources FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

DROP TRIGGER IF EXISTS update_leads_timestamp ON leads;
CREATE TRIGGER update_leads_timestamp BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

DROP TRIGGER IF EXISTS update_lead_insights_timestamp ON lead_insights;
CREATE TRIGGER update_lead_insights_timestamp BEFORE UPDATE ON lead_insights FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

DROP TRIGGER IF EXISTS update_crm_outreach_timestamp ON crm_outreach;
CREATE TRIGGER update_crm_outreach_timestamp BEFORE UPDATE ON crm_outreach FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

DROP TRIGGER IF EXISTS update_competitor_matrix_timestamp ON competitor_matrix;
CREATE TRIGGER update_competitor_matrix_timestamp BEFORE UPDATE ON competitor_matrix FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

-- 10. INDEXES
CREATE INDEX IF NOT EXISTS idx_leads_active_verified ON leads(is_active_verified);
CREATE INDEX IF NOT EXISTS idx_leads_category ON leads(category);
CREATE INDEX IF NOT EXISTS idx_leads_platform ON leads(platform);
CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city);
CREATE INDEX IF NOT EXISTS idx_leads_whatsapp ON leads(whatsapp_number);
CREATE INDEX IF NOT EXISTS idx_lead_insights_score ON lead_insights(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_crm_outreach_status ON crm_outreach(status);
CREATE INDEX IF NOT EXISTS idx_crm_next_follow_up ON crm_outreach(next_follow_up_date);
CREATE INDEX IF NOT EXISTS idx_leads_business_name_trgm ON leads USING gin (business_name gin_trgm_ops);

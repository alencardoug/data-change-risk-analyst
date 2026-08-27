-- The one traceable record per analysed change (FR-017).
-- LangGraph checkpoint tables are created separately by PostgresSaver.setup().

CREATE TABLE IF NOT EXISTS analysis_record (
    id                            TEXT PRIMARY KEY,
    change_request                JSONB NOT NULL,
    structured_change             JSONB,
    evidence                      JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_assessments              JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendations               JSONB NOT NULL DEFAULT '[]'::jsonb,
    review_actions                JSONB NOT NULL DEFAULT '[]'::jsonb,
    reviewed                      BOOLEAN NOT NULL,
    outcome                       TEXT NOT NULL,
    final_recommendation_version  INTEGER NOT NULL,
    step_log                      JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalized_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

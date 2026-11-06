CREATE TABLE "review_metrics" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"repo_id" uuid,
	"provider" text NOT NULL,
	"model" text NOT NULL,
	"latency_ms" integer NOT NULL,
	"input_tokens" integer,
	"output_tokens" integer,
	"cost_usd" numeric(12, 6),
	"success" boolean NOT NULL,
	"error_type" text
);
--> statement-breakpoint
CREATE INDEX "review_metrics_created_at_idx" ON "review_metrics" USING btree ("created_at");
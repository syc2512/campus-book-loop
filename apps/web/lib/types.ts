/**
 * Domain types are generated from the FastAPI OpenAPI document.
 *
 * Regenerate after changing API schemas:
 *   python scripts/export-openapi.py
 *   cd apps/web && npm run gen:api-types
 */
import type { components } from "@/lib/api-types";

type Schemas = components["schemas"];

export type User = Schemas["UserRead"];
export type TokenResponse = Schemas["TokenResponse"];
export type Textbook = Schemas["TextbookRead"];
export type Listing = Schemas["ListingRead"];
export type PriceEstimate = Schemas["PriceEstimateResponse"];
export type ImageUpload = Schemas["ImageUploadResponse"];
export type RecommendationItem = Schemas["RecommendationItem"];
export type RecommendationResponse = Schemas["RecommendationResponse"];
export type Order = Schemas["OrderRead"];
export type AdminOrder = Schemas["AdminOrderRead"];

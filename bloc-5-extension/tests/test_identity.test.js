import { describe, it, expect } from "vitest";
import { normalizeName, identityMatches } from "../content/shared/identity.js";

describe("normalizeName", () => {
  it("lowercases, trims and collapses spaces", () => {
    expect(normalizeName("  Noisyless   SAS ")).toBe("noisyless sas");
  });

  it("strips diacritics", () => {
    expect(normalizeName("Éléonore Média")).toBe("eleonore media");
  });

  it("handles null/undefined", () => {
    expect(normalizeName(null)).toBe("");
    expect(normalizeName(undefined)).toBe("");
  });
});

describe("identityMatches", () => {
  it("matches exact name", () => {
    expect(identityMatches("Noisyless", "Noisyless")).toBe(true);
  });

  it("matches decorated DOM text (bidirectional includes)", () => {
    expect(identityMatches("Noisyless • 123 abonnés", "Noisyless")).toBe(true);
    expect(identityMatches("Publier en tant que Afluxo", "Afluxo")).toBe(true);
  });

  it("is accent and case insensitive", () => {
    expect(identityMatches("AFLUXO", "Afluxo")).toBe(true);
    expect(identityMatches("Société Générale", "Societe Generale")).toBe(true);
  });

  it("rejects a different identity", () => {
    expect(identityMatches("Mathieu Berthod", "Noisyless")).toBe(false);
  });

  it("rejects empty actual name (identity unreadable)", () => {
    expect(identityMatches("", "Noisyless")).toBe(false);
    expect(identityMatches(null, "Noisyless")).toBe(false);
  });
});

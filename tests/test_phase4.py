from graph.neo4j_queries import get_claims_in_year_range

results = get_claims_in_year_range(2022, 2024)
print(f"Claims 2022-2024: {len(results)}")
for r in results[:3]:
    print(f"  [{r['paper_year']}] {r['text'][:80]}")
for r in results:
    assert 2022 <= r["paper_year"] <= 2024, f"Year out of range: {r['paper_year']}"
print("PASS")
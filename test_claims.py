from graph.queries import get_all_claims

claims = get_all_claims()
print(f"Total claims: {len(claims)}")
print()
for c in claims[:5]:
    print(f"[{c['arxiv_id']}] {c['text'][:100]}")
    print()
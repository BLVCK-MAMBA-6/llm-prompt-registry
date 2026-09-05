from registry import PromptRegistry

registry = PromptRegistry()

print("\n--- 1. Testing A/B Routing ---")
# Simulate 4 different users. Based on MD5 hash, they will deterministically 
# get either v1 or v2, but the SAME user will always get the SAME version.
test_users = ["user_001", "user_002", "user_003", "user_004"]

for user in test_users:
    prompt = registry.get("welcome_email", user_id=user, user_name="Sarah", company_name="Acme Corp")
    # Just print the first line to see which version they got
    print(f"{user} got: {prompt.split('.')[0]}")

print("\n--- 2. Testing Version Change ---")
# Let's promote v2 to active for everyone
registry.change_version("welcome_email", "v2")

print("\n--- 3. Testing Rollback ---")
# Oh no, v2 is causing complaints! Roll it back instantly.
registry.rollback("welcome_email")

print("\n--- 4. Verify Rollback ---")
meta = registry.get_metadata("welcome_email")
print(f"Currently running: {meta['active_version']} (Created by: {meta['metadata'].get('author', 'Unknown')})")
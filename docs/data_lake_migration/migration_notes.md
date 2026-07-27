# Migration Notes

## API Keys and User Identity
As of Milestone 5, the CANOE model is transitioning to a centralized configuration model for credentials and identity.

### Deprecated
The following standalone text files previously used to store API keys and tokens are now **deprecated**:
- `input_files/rninja_api_token.txt`
- (And any other standalone `.txt` token files scattered across sectors).

### New Method
All API keys and environment configurations should now be placed in a single `.env` file at the root of the CANOE workspace. 
You can copy `.env.example` to `.env` to get started.

The data lake CLI requires a `CANOE_USER` environment variable. If it is missing from the `.env` file, the system will attempt to fall back to your OS-level username.

import logging

import uvicorn

from app.db import create_engine_and_factory
from app.mcp_server import BearerAuthMiddleware, create_mcp, load_mcp_config

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_mcp_config()
    _engine, session_factory = create_engine_and_factory(config.database_url)
    mcp = create_mcp(config, session_factory)
    app = mcp.streamable_http_app()
    if config.auth_token:
        app = BearerAuthMiddleware(app, config.auth_token)
        logger.info("MCP auth: bearer token enabled")
    else:
        logger.warning("MCP auth: токен не задан, эндпоинт открыт для всей сети")
    logger.info("TermLoop MCP: http://%s:%s/mcp", config.host, config.port)
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


if __name__ == "__main__":
    main()

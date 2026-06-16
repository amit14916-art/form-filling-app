import logging
from urllib.parse import urlparse
from services.portal_strategies.base_strategy import PortalStrategy
from services.portal_strategies.upsc_strategy import UPSCStrategy
from services.portal_strategies.ssc_strategy import SSCStrategy
from services.portal_strategies.ibps_strategy import IBPSStrategy
from services.portal_strategies.nta_strategy import NTAStrategy
from services.portal_strategies.generic_strategy import GenericStrategy

logger = logging.getLogger("StrategyFactory")

class StrategyFactory:
    @staticmethod
    def get_strategy(portal_url: str) -> PortalStrategy:
        """
        Parses the domain of the portal_url and returns the corresponding PortalStrategy.
        Defaults to GenericStrategy.
        """
        if not portal_url:
            return GenericStrategy()

        try:
            parsed = urlparse(portal_url)
            domain = parsed.netloc.lower() or parsed.path.lower()
        except Exception as e:
            logger.error(f"[StrategyFactory] Failed to parse URL '{portal_url}': {e}")
            domain = portal_url.lower()

        logger.info(f"[StrategyFactory] Mapping domain '{domain}' for strategy selection.")

        if "upsconline.nic.in" in domain:
            return UPSCStrategy()
        elif "ssc.gov.in" in domain:
            return SSCStrategy()
        elif "ibps.in" in domain:
            return IBPSStrategy()
        elif "nta.ac.in" in domain:
            return NTAStrategy()
        else:
            logger.info(f"[StrategyFactory] No specialized strategy found for domain '{domain}'. Using GenericStrategy.")
            return GenericStrategy()

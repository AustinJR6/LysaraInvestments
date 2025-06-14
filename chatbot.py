import argparse
import logging

from services.onchain_agent_launcher import launch_agent


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the onchain agent")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode without blockchain interaction",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    launch_agent(test=args.test)

"""
Event Loop Management System

This module provides a cross-platform event loop management system that automatically
selects the optimal event loop implementation based on the operating system and
available dependencies. It ensures maximum performance on supported platforms while
maintaining compatibility across Windows, Linux, and macOS.

Key Features:
    - Automatic detection of operating system
    - Optimal event loop selection (uvloop on Unix-like systems)
    - Graceful fallback to standard asyncio when uvloop is unavailable
    - Windows-specific event loop configuration
    - Thread-safe event loop management
"""

import sys
import asyncio
import platform
from abc import ABC, abstractmethod
from typing import Dict, Any


class LoopFactory(ABC):
    """
    Abstract base class for event loop factories.

    This class defines the interface that all concrete event loop factories
    must implement. It ensures consistent behavior across different platform
    implementations.

    Methods:
        create_loop: Creates a new event loop instance
        get_policy: Returns the event loop policy for the platform
    """

    @abstractmethod
    def create_loop(self) -> asyncio.AbstractEventLoop:
        """
        Create a new event loop instance.

        Returns:
            asyncio.AbstractEventLoop: A new event loop instance configured
            for the specific platform and requirements.

        Raises:
            RuntimeError: If the event loop cannot be created due to
                         platform-specific constraints.
        """
        pass

    @abstractmethod
    def get_policy(self) -> asyncio.AbstractEventLoopPolicy:
        """
        Get the event loop policy for the platform.

        Returns:
            asyncio.AbstractEventLoopPolicy: The event loop policy that
            should be used for this platform configuration.
        """
        pass


class UvloopFactory(LoopFactory):
    """
    UVLoop factory implementation for Unix-like systems (Linux/macOS).

    This factory provides high-performance event loops using the uvloop
    library, which is built on libuv. It typically offers 2-4x performance
    improvement over the standard asyncio event loop.

    Note:
        uvloop is not available on Windows systems. This factory should
        only be used on Unix-like operating systems.

    Example:
         # >>> factory = UvloopFactory()
         # >>> loop = factory.create_loop()
         # >>> isinstance(loop, asyncio.AbstractEventLoop)
         # True
    """

    def create_loop(self) -> asyncio.AbstractEventLoop:
        """
        Create a new uvloop-based event loop.

        Returns:
            asyncio.AbstractEventLoop: A new uvloop event loop instance.

        Raises:
            ImportError: If uvloop is not installed in the current environment.
        """
        import uvloop  # noqa: F401
        return uvloop.new_event_loop()

    def get_policy(self) -> asyncio.AbstractEventLoopPolicy:
        """
        Get the uvloop event loop policy.

        Returns:
            uvloop.EventLoopPolicy: The event loop policy for uvloop.
        """
        import uvloop  # noqa: F401
        return uvloop.EventLoopPolicy()


class WindowsLoopFactory(LoopFactory):
    """
    Windows-specific event loop factory.

    This factory provides optimized event loop configuration for Windows
    systems. It uses ProactorEventLoop for better I/O performance on
    Windows, especially for network operations.

    Note:
        Windows has different I/O characteristics compared to Unix-like
        systems, requiring special event loop configuration.
    """

    def create_loop(self) -> asyncio.AbstractEventLoop:
        """
        Create a Windows-optimized event loop.

        For Python 3.8 and above, this uses WindowsProactorEventLoopPolicy
        which provides better performance and reliability on Windows.

        Returns:
            asyncio.AbstractEventLoop: A Windows-optimized event loop instance.
        """
        if sys.version_info >= (3, 8):
            return asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
        return asyncio.new_event_loop()

    def get_policy(self) -> asyncio.AbstractEventLoopPolicy:
        """
        Get the Windows-optimized event loop policy.

        Returns:
            asyncio.AbstractEventLoopPolicy: The appropriate event loop
            policy for the current Python version on Windows.
        """
        if sys.version_info >= (3, 8):
            return asyncio.WindowsProactorEventLoopPolicy()
        return asyncio.DefaultEventLoopPolicy()


class DefaultLoopFactory(LoopFactory):
    """
    Default event loop factory implementation.

    This factory provides standard asyncio event loops and serves as a
    fallback when platform-specific optimizations are not available or
    appropriate.

    Use Cases:
        - When uvloop is not available on Unix-like systems
        - As a safe fallback for unknown operating systems
        - For maximum compatibility across all environments
    """

    def create_loop(self) -> asyncio.AbstractEventLoop:
        """
        Create a standard asyncio event loop.

        Returns:
            asyncio.AbstractEventLoop: A new standard asyncio event loop.
        """
        return asyncio.new_event_loop()

    def get_policy(self) -> asyncio.AbstractEventLoopPolicy:
        """
        Get the default asyncio event loop policy.

        Returns:
            asyncio.DefaultEventLoopPolicy: The standard event loop policy.
        """
        return asyncio.DefaultEventLoopPolicy()


class EventLoopManager:
    """
    Cross-platform event loop management system.

    This class automatically detects the current operating system and
    available dependencies to provide the optimal event loop configuration
    for the runtime environment.

    Attributes:
        system (str): The normalized operating system name (lowercase)
        factory (LoopFactory): The selected event loop factory instance

    Example:
        # >>> manager = EventLoopManager()
        # >>> loop = manager.setup()
        # >>> info = manager.get_info()
        # >>> print(f"Running on {info['system']} with {info['factory']}")
    """

    def __init__(self):
        """
        Initialize the event loop manager.

        The constructor automatically detects the operating system and
        selects the appropriate event loop factory.
        """
        self.system = platform.system().lower()
        self.factory = self._get_factory()

    def _get_factory(self) -> LoopFactory:
        """
        Select the optimal event loop factory for the current environment.

        Selection Logic:
            - Windows: WindowsLoopFactory
            - Unix-like (Linux/macOS): UvloopFactory (if available)
            - Fallback: DefaultLoopFactory

        Returns:
            LoopFactory: The selected event loop factory instance.

        Raises:
            ValueError: If the operating system cannot be determined.
        """
        if self.system == 'windows':
            return WindowsLoopFactory()

        # Attempt to use uvloop on non-Windows systems
        try:
            # Import check - will raise ImportError if uvloop is not available
            import uvloop
            return UvloopFactory()
        except ImportError:
            print("⚠️  uvloop is not available, falling back to default event loop")
            return DefaultLoopFactory()

    def setup(self) -> asyncio.AbstractEventLoop:
        """
        Configure and return the optimal event loop for the current platform.

        This method:
            1. Sets the appropriate event loop policy
            2. Creates a new event loop instance
            3. Sets it as the current event loop
            4. Returns the configured loop

        Returns:
            asyncio.AbstractEventLoop: The configured event loop instance.

        Example:
            # >>> manager = EventLoopManager()
            # >>> loop = manager.setup()
            # >>> asyncio.get_event_loop() is loop
            # True
        """
        # Configure event loop policy
        policy = self.factory.get_policy()
        asyncio.set_event_loop_policy(policy)

        # Create and set the event loop
        loop = self.factory.create_loop()
        asyncio.set_event_loop(loop)

        print(f"✅ System: {self.system}, Using: {self.factory.__class__.__name__}")
        return loop

    def get_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the current event loop configuration.

        Returns:
            Dict[str, Any]: Configuration information including:
                - system: Operating system name
                - factory: Factory class name in use
                - uvloop_available: Whether uvloop is available
                - python_version: Python version string

        Example:
             # >>> info = manager.get_info()
             # >>> print(f"Platform: {info['system']}")
             # >>> print(f"UVLoop available: {info['uvloop_available']}")
        """
        return {
            "system": self.system,
            "factory": self.factory.__class__.__name__,
            "uvloop_available": self._is_uvloop_available(),
            "python_version": platform.python_version()
        }

    @staticmethod
    def _is_uvloop_available() -> bool:
        """
        Check if uvloop is available in the current environment.

        Returns:
            bool: True if uvloop can be imported, False otherwise.

        Note:
            This method performs a simple import check and does not
            validate uvloop functionality or version compatibility.
        """
        try:
            import uvloop
            return True
        except ImportError:
            return False


def create_demo_task() -> str:
    """
    Create and run a demonstration asynchronous task.

    This function demonstrates basic usage of the event loop manager
    by creating and running a simple asynchronous task.

    Returns:
        str: The result of the demo task execution.

    Example:
         # >>> result = create_demo_task()
         # >>> print(result)
         # 'Demo task completed successfully'
    """
    # Initialize event loop manager
    manager = EventLoopManager()

    # Display configuration information
    info = manager.get_info()
    print(f"🔧 Configuration: {info}")

    # Configure event loop
    loop = manager.setup()

    # Define demo coroutine
    async def demo_coroutine():
        """Example coroutine demonstrating async operation."""
        print("🚀 Starting asynchronous task...")
        await asyncio.sleep(1)  # Simulate async I/O operation
        print("✅ Asynchronous task completed successfully")
        return "Demo task completed successfully"

    # Execute the coroutine
    try:
        result = loop.run_until_complete(demo_coroutine())
        return result
    except Exception as e:
        print(f"❌ Error executing demo task: {e}")
        raise
    finally:
        # Cleanup
        loop.close()


def main():
    """
    Main execution function demonstrating the event loop management system.

    This function serves as both a demonstration and test of the event
    loop management functionality. It shows typical usage patterns and
    provides immediate visual feedback about the system configuration.

    Execution Flow:
        1. Initialize EventLoopManager
        2. Display system configuration
        3. Setup optimal event loop
        4. Execute demo task
        5. Display results

    Example:
        #  >>> main()
        🔧 Configuration: {'system': 'linux', 'factory': 'UvloopFactory', ...}
        ✅ System: linux, Using: UvloopFactory
        🚀 Starting asynchronous task...
        ✅ Asynchronous task completed successfully
        📊 Demo result: Demo task completed successfully
    """
    try:
        result = create_demo_task()
        print(f"📊 Demo result: {result}")
    except Exception as e:
        print(f"💥 Demo execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Entry point when executed as a script
    main()

# Additional Usage Examples
"""
Advanced Usage Examples:

1. Integration with Web Frameworks:

    # FastAPI Integration
    from fastapi import FastAPI
    import uvicorn

    manager = EventLoopManager()
    loop = manager.setup()

    app = FastAPI()

    if __name__ == "__main__":
        config = uvicorn.Config(app, loop=loop)
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())

2. Custom Application Integration:

    manager = EventLoopManager()
    loop = manager.setup()

    async def main_application():
        # Your application logic here
        pass

    try:
        loop.run_until_complete(main_application())
    finally:
        loop.close()

3. Testing and Debugging:

    manager = EventLoopManager()
    info = manager.get_info()
    print(f"Testing environment: {info}")

    # Verify uvloop availability
    if info['uvloop_available'] and info['system'] != 'windows':
        assert info['factory'] == 'UvloopFactory'
    elif info['system'] == 'windows':
        assert info['factory'] == 'WindowsLoopFactory'

Performance Characteristics:
    - uvloop (Unix-like): 2-4x performance improvement
    - Windows Proactor: Optimized for Windows I/O
    - Default: Maximum compatibility, standard performance

Dependencies:
    - uvloop: Optional dependency for Unix-like systems
    - Python 3.7+: Required for full functionality
    - asyncio: Built-in Python library

Compatibility:
    - Windows 7+ (with Python 3.7+)
    - Linux (kernel 2.6.18+)
    - macOS 10.9+
    - FreeBSD, OpenBSD, NetBSD

Security Considerations:
    - No external network calls
    - Only uses built-in platform detection
    - Safe for use in restricted environments
"""
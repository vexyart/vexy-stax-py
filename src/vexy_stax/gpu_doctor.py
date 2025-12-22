# this_file: vexy-stax-py/src/vexy_stax/gpu_doctor.py
"""GPU diagnostics for vexy-stax renderer."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass


@dataclass(slots=True)
class GPUDiagnostics:
    """Results of GPU capability check."""

    available: bool
    adapter_name: str
    backend: str
    platform: str
    python_version: str
    is_software: bool = False
    error: str | None = None


SOFTWARE_ADAPTERS = frozenset(
    {
        "llvmpipe",
        "swiftshader",
        "lavapipe",
        "mesa",
        "software",
        "cpu",
    }
)


def _is_software_adapter(adapter_name: str, adapter_type: str) -> bool:
    """Check if adapter is software-based (CPU rendering)."""
    name_lower = adapter_name.lower()
    type_lower = adapter_type.lower()

    # Check adapter type first
    if "software" in type_lower or "cpu" in type_lower:
        return True

    # Check known software adapter names
    return any(sw in name_lower for sw in SOFTWARE_ADAPTERS)


def diagnose_gpu() -> GPUDiagnostics:
    """Probe GPU and return diagnostics.

    Returns detailed information about GPU availability including
    adapter name, backend type, and any errors encountered.
    """
    base = GPUDiagnostics(
        available=False,
        adapter_name="Unknown",
        backend="Unknown",
        platform=f"{platform.system()} {platform.release()}",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    try:
        from wgpu.utils import get_default_device

        device = get_default_device()
        adapter = device.adapter

        # Extract adapter info
        info = adapter.info
        adapter_name = info.get("device", "Unknown Device")
        backend = info.get("backend_type", "Unknown")
        vendor = info.get("vendor", "")
        adapter_type = info.get("adapter_type", "")

        # Format adapter name with vendor
        if vendor and vendor not in adapter_name:
            adapter_name = f"{vendor} {adapter_name}"

        # Detect software rendering
        is_software = _is_software_adapter(adapter_name, adapter_type)

        return GPUDiagnostics(
            available=True,
            adapter_name=adapter_name,
            backend=backend,
            platform=base.platform,
            python_version=base.python_version,
            is_software=is_software,
        )

    except ImportError as exc:
        return GPUDiagnostics(
            available=False,
            adapter_name="N/A",
            backend="N/A",
            platform=base.platform,
            python_version=base.python_version,
            error=f"wgpu not installed: {exc}",
        )
    except RuntimeError as exc:
        return GPUDiagnostics(
            available=False,
            adapter_name="N/A",
            backend="N/A",
            platform=base.platform,
            python_version=base.python_version,
            error=str(exc),
        )
    except Exception as exc:
        return GPUDiagnostics(
            available=False,
            adapter_name="N/A",
            backend="N/A",
            platform=base.platform,
            python_version=base.python_version,
            error=f"Unexpected error: {exc}",
        )


def format_diagnostics(diag: GPUDiagnostics) -> str:
    """Format diagnostics for terminal display."""
    lines = [
        "GPU Diagnostics",
        "=" * 40,
        f"Platform:    {diag.platform}",
        f"Python:      {diag.python_version}",
        "",
    ]

    if diag.available:
        if diag.is_software:
            lines.extend(
                [
                    "⚠️  Software Rendering (CPU)",
                    f"   Adapter: {diag.adapter_name}",
                    f"   Backend: {diag.backend}",
                    "",
                    "Rendering will work but may be slow.",
                    "For production, install GPU drivers.",
                ]
            )
        else:
            lines.extend(
                [
                    "✅ GPU Available",
                    f"   Adapter: {diag.adapter_name}",
                    f"   Backend: {diag.backend}",
                    "",
                    "The pygfx renderer should work correctly.",
                ]
            )
    else:
        lines.extend(
            [
                "❌ GPU Not Available",
                f"   Error: {diag.error}",
                "",
                "Recommendations:",
            ]
        )

        # Platform-specific advice
        if "darwin" in diag.platform.lower():
            lines.append("  • macOS: Requires macOS 10.13+ with Metal support")
        elif "linux" in diag.platform.lower():
            lines.extend(
                [
                    "  • Linux: Install Vulkan drivers for your GPU",
                    "  • Try: sudo apt install vulkan-tools mesa-vulkan-drivers",
                ]
            )
        elif "windows" in diag.platform.lower():
            lines.append(
                "  • Windows: Install latest GPU drivers with DirectX 12 or Vulkan"
            )
        else:
            lines.append("  • Ensure GPU drivers are installed")

        lines.extend(
            [
                "",
                "Software rendering options:",
                "  • Linux: export WGPU_ADAPTER_NAME=llvmpipe",
                "  • Any: export WGPU_ADAPTER_NAME=SwiftShader",
                "",
                "Fallback: Use --backend=playwright (requires dev server)",
            ]
        )

    return "\n".join(lines)


class SoftwareRenderingError(Exception):
    """Raised when software rendering is detected but not allowed."""

    pass


def check_gpu_requirements(*, require_hardware: bool = False) -> GPUDiagnostics:
    """Check GPU and optionally require hardware acceleration.

    Args:
        require_hardware: If True, raise SoftwareRenderingError when software
                         rendering is detected.

    Returns:
        GPUDiagnostics with adapter info.

    Raises:
        SoftwareRenderingError: When require_hardware=True and only software
                               rendering is available.
        RuntimeError: When GPU is completely unavailable.
    """
    diag = diagnose_gpu()

    if not diag.available:
        raise RuntimeError(f"GPU not available: {diag.error}")

    if require_hardware and diag.is_software:
        raise SoftwareRenderingError(
            f"Software rendering detected ({diag.adapter_name}). "
            f"Use --allow-software to proceed anyway, or install GPU drivers."
        )

    return diag


__all__ = [
    "GPUDiagnostics",
    "SoftwareRenderingError",
    "check_gpu_requirements",
    "diagnose_gpu",
    "format_diagnostics",
]

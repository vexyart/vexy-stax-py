# this_file: tests/test_gpu_doctor.py
"""Tests for GPU diagnostics module."""

from __future__ import annotations


import pytest

from vexy_stax.gpu_doctor import (
    GPUDiagnostics,
    SoftwareRenderingError,
    _is_software_adapter,
    check_gpu_requirements,
    diagnose_gpu,
    format_diagnostics,
)


def test_gpu_diagnostics_dataclass_stores_fields() -> None:
    diag = GPUDiagnostics(
        available=True,
        adapter_name="Test GPU",
        backend="Metal",
        platform="Darwin 24.0",
        python_version="3.12.0",
    )

    assert diag.available is True
    assert diag.adapter_name == "Test GPU"
    assert diag.backend == "Metal"
    assert diag.platform == "Darwin 24.0"
    assert diag.python_version == "3.12.0"
    assert diag.error is None


def test_gpu_diagnostics_with_error() -> None:
    diag = GPUDiagnostics(
        available=False,
        adapter_name="N/A",
        backend="N/A",
        platform="Linux 5.0",
        python_version="3.12.0",
        error="No GPU adapter found",
    )

    assert diag.available is False
    assert diag.error == "No GPU adapter found"


def test_diagnose_gpu_returns_diagnostics() -> None:
    """Smoke test: diagnose_gpu returns valid GPUDiagnostics."""
    diag = diagnose_gpu()

    assert isinstance(diag, GPUDiagnostics)
    assert isinstance(diag.available, bool)
    assert isinstance(diag.platform, str)
    assert isinstance(diag.python_version, str)
    assert len(diag.python_version.split(".")) == 3


def test_format_diagnostics_when_available_shows_success() -> None:
    diag = GPUDiagnostics(
        available=True,
        adapter_name="Apple M1",
        backend="Metal",
        platform="Darwin 24.0",
        python_version="3.12.0",
    )

    output = format_diagnostics(diag)

    assert "GPU Diagnostics" in output
    assert "✅ GPU Available" in output
    assert "Apple M1" in output
    assert "Metal" in output
    assert "Darwin 24.0" in output
    assert "3.12.0" in output
    assert "pygfx renderer should work" in output


def test_format_diagnostics_when_unavailable_shows_error() -> None:
    diag = GPUDiagnostics(
        available=False,
        adapter_name="N/A",
        backend="N/A",
        platform="Linux 5.0",
        python_version="3.12.0",
        error="No suitable GPU adapter",
    )

    output = format_diagnostics(diag)

    assert "❌ GPU Not Available" in output
    assert "No suitable GPU adapter" in output
    assert "Recommendations:" in output
    assert "Fallback:" in output


def test_format_diagnostics_linux_shows_vulkan_advice() -> None:
    diag = GPUDiagnostics(
        available=False,
        adapter_name="N/A",
        backend="N/A",
        platform="Linux 5.15.0",
        python_version="3.12.0",
        error="No GPU",
    )

    output = format_diagnostics(diag)

    assert "vulkan" in output.lower()


def test_format_diagnostics_macos_shows_metal_advice() -> None:
    diag = GPUDiagnostics(
        available=False,
        adapter_name="N/A",
        backend="N/A",
        platform="Darwin 24.0",
        python_version="3.12.0",
        error="No GPU",
    )

    output = format_diagnostics(diag)

    assert "Metal" in output


def test_format_diagnostics_windows_shows_directx_advice() -> None:
    diag = GPUDiagnostics(
        available=False,
        adapter_name="N/A",
        backend="N/A",
        platform="Windows 10",
        python_version="3.12.0",
        error="No GPU",
    )

    output = format_diagnostics(diag)

    assert "DirectX" in output or "Vulkan" in output


def test_is_software_adapter_detects_llvmpipe() -> None:
    assert _is_software_adapter("llvmpipe (LLVM 15.0.6)", "") is True


def test_is_software_adapter_detects_swiftshader() -> None:
    assert _is_software_adapter("SwiftShader Device", "") is True


def test_is_software_adapter_detects_lavapipe() -> None:
    assert _is_software_adapter("lavapipe", "") is True


def test_is_software_adapter_detects_by_type() -> None:
    assert _is_software_adapter("Unknown Device", "software") is True
    assert _is_software_adapter("Unknown Device", "cpu") is True


def test_is_software_adapter_hardware_gpu_returns_false() -> None:
    assert _is_software_adapter("Apple M1", "discrete") is False
    assert _is_software_adapter("NVIDIA GeForce RTX 4090", "") is False
    assert _is_software_adapter("AMD Radeon RX 7900", "integrated") is False


def test_format_diagnostics_software_shows_warning() -> None:
    diag = GPUDiagnostics(
        available=True,
        adapter_name="llvmpipe (LLVM 15.0.6)",
        backend="Vulkan",
        platform="Linux 5.15.0",
        python_version="3.12.0",
        is_software=True,
    )

    output = format_diagnostics(diag)

    assert "Software Rendering" in output
    assert "may be slow" in output
    assert "llvmpipe" in output


def test_check_gpu_requirements_returns_diagnostics(monkeypatch) -> None:
    """check_gpu_requirements returns GPUDiagnostics when GPU available."""
    mock_diag = GPUDiagnostics(
        available=True,
        adapter_name="Apple M1",
        backend="Metal",
        platform="Darwin",
        python_version="3.12.0",
        is_software=False,
    )
    monkeypatch.setattr("vexy_stax.gpu_doctor.diagnose_gpu", lambda: mock_diag)

    result = check_gpu_requirements(require_hardware=False)

    assert result.available is True
    assert result.adapter_name == "Apple M1"


def test_check_gpu_requirements_raises_when_gpu_unavailable(monkeypatch) -> None:
    """check_gpu_requirements raises RuntimeError when GPU unavailable."""
    mock_diag = GPUDiagnostics(
        available=False,
        adapter_name="N/A",
        backend="N/A",
        platform="Linux",
        python_version="3.12.0",
        error="No GPU adapter found",
    )
    monkeypatch.setattr("vexy_stax.gpu_doctor.diagnose_gpu", lambda: mock_diag)

    with pytest.raises(RuntimeError, match="GPU not available"):
        check_gpu_requirements()


def test_check_gpu_requirements_raises_on_software_when_required(monkeypatch) -> None:
    """check_gpu_requirements raises SoftwareRenderingError when hardware required."""
    mock_diag = GPUDiagnostics(
        available=True,
        adapter_name="llvmpipe (LLVM 15.0.6)",
        backend="Vulkan",
        platform="Linux",
        python_version="3.12.0",
        is_software=True,
    )
    monkeypatch.setattr("vexy_stax.gpu_doctor.diagnose_gpu", lambda: mock_diag)

    with pytest.raises(SoftwareRenderingError, match="Software rendering detected"):
        check_gpu_requirements(require_hardware=True)


def test_check_gpu_requirements_allows_software_by_default(monkeypatch) -> None:
    """check_gpu_requirements allows software rendering when not requiring hardware."""
    mock_diag = GPUDiagnostics(
        available=True,
        adapter_name="llvmpipe (LLVM 15.0.6)",
        backend="Vulkan",
        platform="Linux",
        python_version="3.12.0",
        is_software=True,
    )
    monkeypatch.setattr("vexy_stax.gpu_doctor.diagnose_gpu", lambda: mock_diag)

    # Should NOT raise - software rendering allowed by default
    result = check_gpu_requirements(require_hardware=False)

    assert result.is_software is True
    assert result.adapter_name == "llvmpipe (LLVM 15.0.6)"


def test_software_rendering_error_message_includes_adapter_name(monkeypatch) -> None:
    """SoftwareRenderingError message mentions the adapter name."""
    mock_diag = GPUDiagnostics(
        available=True,
        adapter_name="SwiftShader Device",
        backend="Vulkan",
        platform="Linux",
        python_version="3.12.0",
        is_software=True,
    )
    monkeypatch.setattr("vexy_stax.gpu_doctor.diagnose_gpu", lambda: mock_diag)

    with pytest.raises(SoftwareRenderingError) as exc_info:
        check_gpu_requirements(require_hardware=True)

    assert "SwiftShader Device" in str(exc_info.value)
    assert "--allow-software" in str(exc_info.value)

# Vexy Stax

Browser-based tools for arranging images along the Z-axis in 3D space with interactive controls and export capabilities.

## Projects

This repository contains two implementations:

### vexy-stax-wt (Tweakpane Edition)
**Status**: ✅ Production-ready

Browser-based tool using vanilla Three.js + Tweakpane for UI controls.

- **Tech stack**: Three.js, Tweakpane, Vite
- **Architecture**: Vanilla JavaScript (imperative)
- **Bundle size**: ~650KB gzipped
- **Best for**: Minimal dependencies, smaller bundle, standalone use

**Features**:
- Drag-and-drop image loading
- Multiple camera modes (Perspective, Orthographic, Isometric, Telephoto)
- Adjustable Z-spacing between layers
- Viewpoint presets (Front, Top, Isometric, Side, 3D Stack View)
- Export to PNG (1x, 2x, 4x resolution)
- Export/import JSON configuration
- Material presets (Matte, Glossy, Plastic, etc.)
- Transparent background support
- Image reordering via drag-and-drop

[See vexy-stax-wt/README.md for details](vexy-stax-wt/README.md)

---

### vexy-stax-wl (Leva Edition)
**Status**: 📋 Planning phase only

Planned React-based rewrite using react-three-fiber + leva for UI controls.

- **Tech stack**: React, react-three-fiber, @react-three/drei, leva
- **Architecture**: React components (declarative)
- **Bundle size**: ~810KB gzipped (+160KB React overhead)
- **Best for**: React projects, component reusability, automatic state management

**Key difference**: Leva is React-only (no vanilla JS support), requiring complete architectural rewrite from vexy-stax-wt.

**Current state**: Comprehensive planning documentation exists:
- PLAN.md (25KB): 8-phase implementation plan
- TODO.md: 70+ itemized tasks
- DEPENDENCIES.md: Package justifications
- Estimated implementation: 21-29 hours

**Why create this variant?**
- Exploration of leva as alternative to Tweakpane
- Demonstrates React/R3F architectural patterns
- Component-based 3D scene construction
- Automatic lifecycle management

[See vexy-stax-wl/PLAN.md for details](vexy-stax-wl/PLAN.md)

---

## Quick Start

### vexy-stax-wt (Ready to use)
```bash
cd vexy-stax-wt
npm install
npm run dev
# Open http://localhost:5173
```

### vexy-stax-wl (Planning only)
Implementation not yet started. See PLAN.md for architecture details.

---

## Comparison

| Feature | vexy-stax-wt | vexy-stax-wl |
|---------|--------------|--------------|
| Status | ✅ Production | 📋 Planning |
| Framework | Vanilla JS | React |
| 3D Library | Three.js | react-three-fiber |
| UI Library | Tweakpane | leva |
| Architecture | Imperative | Declarative |
| Bundle Size | ~650KB | ~810KB |
| Learning Curve | Three.js | React + R3F |
| State Management | Manual | Automatic |

---

## Features (vexy-stax-wt)

### Image Management
- Load multiple PNG/JPG images
- Drag-and-drop interface
- Image reordering (affects Z-stack)
- Individual image deletion
- Original dimensions preserved

### 3D Controls
- **Camera Modes**:
  - Perspective: Natural 3D view
  - Orthographic: No perspective distortion
  - Isometric: 45° angled view
  - Telephoto: Distant camera, minimal distortion
- **Z-Spacing**: 0-500px distance between layers
- **Zoom**: 0.1x to 3.0x
- **FOV**: 15° to 120° (perspective modes)

### Export Options
- **PNG**: 1x, 2x, or 4x resolution
- **JSON**: Complete scene configuration with embedded images
- Transparent background support
- Copy/paste configuration via clipboard

### Material Presets
- Flat Matte
- Glossy Photo
- Plastic Card
- Thick Board
- Metal Sheet
- Glass Slide
- Bordered frames
- 3D Box

---

## Documentation

- [TODO.md](TODO.md) - Task tracking and quality improvements
- [WORK.md](WORK.md) - Development progress log
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [test.sh](test.sh) - Automated test suite

### Project-Specific Docs

**vexy-stax-wt**:
- README.md
- CHANGELOG.md
- TEST_REPORT.md

**vexy-stax-wl**:
- PLAN.md (comprehensive implementation plan)
- TODO.md (itemized tasks)
- WORK.md (status tracking)
- CHANGELOG.md (planning phase log)
- DEPENDENCIES.md (package justifications)

---

## Testing

Run automated tests:
```bash
./test.sh
```

Run Python unit tests (pytest):
```bash
uvx hatch test
```

Tests validate:
- PNG output format and dimensions
- Project structure completeness
- Documentation presence

---

## Architecture Notes

### vexy-stax-wt: Imperative Approach
Scene construction requires manual Three.js object management:
```javascript
const geometry = new THREE.PlaneGeometry(width, height);
const material = new THREE.MeshStandardMaterial({ map: texture });
const mesh = new THREE.Mesh(geometry, material);
scene.add(mesh);
```

State updates trigger manual UI refresh:
```javascript
pane.addBinding(params, 'zSpacing').on('change', (ev) => {
  updateZSpacing(ev.value);
});
```

### vexy-stax-wl: Declarative Approach
Scene construction uses JSX components:
```jsx
<mesh position={[0, 0, zPosition]}>
  <planeGeometry args={[width, height]} />
  <meshStandardMaterial map={texture} />
</mesh>
```

State updates trigger automatic re-renders:
```javascript
const { zSpacing } = useControls({
  zSpacing: { value: 100, min: 0, max: 500 }
});
// React handles updates automatically
```

---

## Browser Support

- Chrome/Edge: ✅ Fully supported
- Firefox: ✅ Fully supported
- Safari: ✅ Fully supported (macOS/iOS)

Requires:
- WebGL support
- FileReader API
- Modern JavaScript (ES6+)

---

## License

ISC

---

## Author

Adam Twardoch <adam+npm@twardoch.com>
https://twardoch.github.io/

---

## Development Status

| Project | Status | Completion |
|---------|--------|------------|
| vexy-stax-wt | ✅ Production | 100% |
| vexy-stax-wl | 📋 Planning | 0% (docs: 100%) |

---

## Choosing Between Variants

**Choose vexy-stax-wt if you want:**
- Smaller bundle size
- No React dependency
- Production-ready tool today
- Vanilla JavaScript codebase

**Choose vexy-stax-wl if you want:**
- React-based architecture
- Component reusability
- Declarative scene construction
- Automatic state management
- Modern React patterns

**Note**: vexy-stax-wl is planning-phase only. For immediate use, choose vexy-stax-wt.

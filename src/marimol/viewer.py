from __future__ import annotations

import os

import anywidget
import marimo as mo
import traitlets

from .utils import (
    ATOMIC_RADII,
    CPK_COLORS,
    DEFAULT_COLOR,
    DEFAULT_RADIUS,
    DEFAULT_VDW_RADIUS,
    VDW_RADII,
    parse_toml_config,
    resolve_color,
)


class MoleculeViewerWidget(anywidget.AnyWidget):
    """
    A widget for visualizing molecules and periodic structures.
    """

    _esm = """
    import * as THREE from 'https://esm.sh/three@0.160.0';
    import { TrackballControls } from 'https://esm.sh/three@0.160.0/addons/controls/TrackballControls.js';

    export default {
        render({ model, el }) {
            // Container setup
            const container = document.createElement('div');
            container.style.width = model.get('width') || '100%';
            container.style.height = model.get('height') || '400px';
            container.style.display = 'block';
            container.style.position = 'relative';
            container.style.backgroundColor = model.get('background_color') || '#ffffff';
            container.style.overflow = 'hidden';

            const applyOutline = () => {
                const outl = model.get('viewer_outline');
                if (outl === true) {
                    container.style.border = '1px solid #ccc';
                    container.style.borderRadius = '4px';
                } else if (typeof outl === 'string' && outl.length > 0) {
                    container.style.border = outl;
                    container.style.borderRadius = '4px';
                } else {
                    container.style.border = 'none';
                    container.style.borderRadius = '0px';
                }
            };
            applyOutline();
            el.appendChild(container);

            // Three.js setup
            const scene = new THREE.Scene();

            // Add lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
            scene.add(ambientLight);

            const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.7);
            dirLight1.position.set(10, 10, 10);
            scene.add(dirLight1);

            const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
            dirLight2.position.set(-10, -10, -10);
            scene.add(dirLight2);

            const persCamera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            const orthoCamera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 1000);
            let camera = model.get('projection') === 'orthographic' ? orthoCamera : persCamera;

            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.autoClear = false; // We need to manage clearing for multiple viewports
            renderer.domElement.style.position = 'absolute';
            renderer.domElement.style.top = '0';
            renderer.domElement.style.left = '0';
            renderer.domElement.style.width = '100%';
            renderer.domElement.style.height = '100%';
            renderer.domElement.style.display = 'block';
            container.appendChild(renderer.domElement);

            // Axes setup (overlay)
            const axesScene = new THREE.Scene();

            // Custom Thick Axes
            const createAxis = (color, euler) => {
                const material = new THREE.MeshBasicMaterial({ color: color });
                const geometry = new THREE.CylinderGeometry(0.06, 0.06, 1.5, 8);
                geometry.translate(0, 0.75, 0);
                const mesh = new THREE.Mesh(geometry, material);
                mesh.setRotationFromEuler(euler);
                axesScene.add(mesh);
            };

            createAxis(0xff4444, new THREE.Euler(0, 0, -Math.PI/2)); // X (Red)
            createAxis(0x44ff44, new THREE.Euler(0, 0, 0));          // Y (Green)
            createAxis(0x4444ff, new THREE.Euler(Math.PI/2, 0, 0));  // Z (Blue)

            // Canvas sprites for Labels
            // Canvas sprites for Labels
            const createLabel = (text, color, pos, depthTest = true) => {
                const canvas = document.createElement('canvas');
                canvas.width = 128; canvas.height = 128;
                const ctx = canvas.getContext('2d');
                ctx.font = 'bold 96px sans-serif';
                ctx.fillStyle = color;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(text, 64, 64);

                const texture = new THREE.CanvasTexture(canvas);
                const spriteMat = new THREE.SpriteMaterial({ map: texture, depthTest: depthTest });
                const sprite = new THREE.Sprite(spriteMat);
                sprite.position.copy(pos);
                sprite.name = text; // Give a name for raycasting identification
                return sprite;
            };

            const xLbl = createLabel('X', '#ff4444', new THREE.Vector3(1.8, 0, 0), true);
            xLbl.scale.set(1.2, 1.2, 1.2); axesScene.add(xLbl);

            const yLbl = createLabel('Y', '#44ff44', new THREE.Vector3(0, 1.8, 0), true);
            yLbl.scale.set(1.2, 1.2, 1.2); axesScene.add(yLbl);

            const zLbl = createLabel('Z', '#4444ff', new THREE.Vector3(0, 0, 1.8), true);
            zLbl.scale.set(1.2, 1.2, 1.2); axesScene.add(zLbl);
            // Orthographic bounds: left, right, top, bottom, near, far
            const axesCamera = new THREE.OrthographicCamera(-2.5, 2.5, 2.5, -2.5, 0.1, 10);

            const controls = new TrackballControls(camera, renderer.domElement);
            controls.rotateSpeed = 3.0;
            controls.zoomSpeed = 1.2;
            controls.panSpeed = 0.8;
            controls.noPan = true; // We use custom panning via setViewOffset to preserve the rotation center

            // Geometry and Material for Atoms
            // We use a high segment count for smooth spheres, but InstancedMesh keeps it incredibly fast
            const sphereGeometry = new THREE.SphereGeometry(1, 32, 32);
            const sphereMaterial = new THREE.MeshPhongMaterial({
                color: 0xffffff,
                shininess: 60
            });
            const cylinderGeometry = new THREE.CylinderGeometry(1, 1, 1, 16);
            const cylinderMaterial = new THREE.MeshPhongMaterial({
                color: 0xffffff,
                shininess: 60
            });

            const outlineMaterial = new THREE.MeshBasicMaterial({
                color: 0xffffff,
                side: THREE.BackSide,
                depthWrite: true
            });

            const bondOutlineMaterial = new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.BackSide,
                depthWrite: true
            });

            const selectedOutlineColor = new THREE.Color(0x00f0ff);
            const defaultOutlineColor = new THREE.Color(0x000000);

            let atomMesh = null; // InstancedMesh for atoms
            let bondMesh = null; // InstancedMesh for bonds
            let atomOutlineMesh = null;
            let bondOutlineMesh = null;
            let cellGroup = null; // Group containing cell lines and labels
            const dummy = new THREE.Object3D();
            const colorObj = new THREE.Color();
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();
            const yAxis = new THREE.Vector3(0, 1, 0);

            let currentPositions = [];
            let currentSpecies = [];
            let currentNumAtoms = 0;
            let currentStyle = {};
            let currentGetRadius = (sp) => 0.8;

            // --- Atom Labels Overlay ---
            const labelsContainer = document.createElement('div');
            labelsContainer.style.position = 'absolute';
            labelsContainer.style.top = '0';
            labelsContainer.style.left = '0';
            labelsContainer.style.width = '100%';
            labelsContainer.style.height = '100%';
            labelsContainer.style.pointerEvents = 'none';
            labelsContainer.style.overflow = 'hidden';
            labelsContainer.style.zIndex = '5';
            container.appendChild(labelsContainer);
            let labelElements = [];

            // --- Trajectory UI Overlay ---
            const uiContainer = document.createElement('div');
            uiContainer.style.position = 'absolute';
            uiContainer.style.top = '15px';
            uiContainer.style.left = '15px';
            uiContainer.style.zIndex = '10';
            uiContainer.style.display = 'none'; // hidden by default
            uiContainer.style.flexWrap = 'wrap';
            uiContainer.style.maxWidth = 'calc(100% - 70px)';
            uiContainer.style.background = 'rgba(255, 255, 255, 0.7)';
            uiContainer.style.backdropFilter = 'blur(10px)';
            uiContainer.style.WebkitBackdropFilter = 'blur(10px)';
            uiContainer.style.borderRadius = '8px';
            uiContainer.style.padding = '6px 10px';
            uiContainer.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            uiContainer.style.fontFamily = 'sans-serif';
            uiContainer.style.fontSize = '14px';
            uiContainer.style.color = '#333';
            uiContainer.style.alignItems = 'center';
            uiContainer.style.gap = '6px';

            const createBtn = (htmlContent, onClick) => {
                const btn = document.createElement('button');
                btn.innerHTML = htmlContent;
                btn.style.background = 'transparent';
                btn.style.border = 'none';
                btn.style.outline = 'none';
                btn.style.borderRadius = '4px';
                btn.style.cursor = 'pointer';
                btn.style.padding = '4px';
                btn.style.display = 'flex';
                btn.style.alignItems = 'center';
                btn.style.justifyContent = 'center';
                btn.style.transition = 'transform 0.2s, background 0.2s';
                btn.onclick = onClick;
                btn.onmouseover = () => { btn.style.transform = 'scale(1.1)'; btn.style.background = 'rgba(0,0,0,0.08)'; };
                btn.onmouseout = () => { btn.style.transform = 'scale(1)'; btn.style.background = 'transparent'; };
                return btn;
            };

            const svgIcon = (path) => `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="${path}"></path></svg>`;

            const iconFirst = svgIcon("M18.41 16.59L13.82 12l4.59-4.59L17 6l-6 6 6 6z M6 6h2v12H6z");
            const iconPrev = svgIcon("M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6 1.41-1.41z");
            const iconPlay = svgIcon("M8 5v14l11-7z");
            const iconPause = svgIcon("M6 19h4V5H6v14zm8-14v14h4V5h-4z");
            const iconNext = svgIcon("M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z");
            const iconLast = svgIcon("M5.59 7.41L10.18 12l-4.59 4.59L7 18l6-6-6-6z M16 6h2v12h-2z");

            let animationInterval = null;
            let isPlaying = false;

            const btnFirst = createBtn(iconFirst, () => setFrame(0));
            const btnPrev = createBtn(iconPrev, () => setFrame(model.get('current_frame') - 1));
            const btnPlay = createBtn(iconPlay, () => togglePlay());
            btnPlay.style.display = model.get('multi_traj') !== false ? 'flex' : 'none';
            const btnNext = createBtn(iconNext, () => setFrame(model.get('current_frame') + 1));
            const btnLast = createBtn(iconLast, () => {
                const frames = model.get('data');
                if (frames && frames.length > 0) setFrame(frames.length - 1);
            });

            const btnGroup = document.createElement('div');
            btnGroup.style.display = 'flex';
            btnGroup.style.alignItems = 'center';
            btnGroup.style.gap = '2px';
            btnGroup.appendChild(btnFirst);
            btnGroup.appendChild(btnPrev);
            btnGroup.appendChild(btnPlay);
            btnGroup.appendChild(btnNext);
            btnGroup.appendChild(btnLast);

            const frameSlider = document.createElement('input');
            frameSlider.type = 'range';
            frameSlider.min = '0';
            frameSlider.max = '0';
            frameSlider.value = '0';
            frameSlider.step = '1';
            frameSlider.style.display = model.get('trajectory_slider') ? 'block' : 'none';
            frameSlider.style.cursor = 'pointer';
            frameSlider.style.accentColor = '#555';
            frameSlider.style.flex = '1 1 80px';
            frameSlider.style.minWidth = '50px';
            frameSlider.style.maxWidth = '120px';
            frameSlider.style.width = '100px';
            frameSlider.style.margin = '0';
            frameSlider.addEventListener('input', (e) => {
                setFrame(parseInt(e.target.value, 10));
            });
            frameSlider.addEventListener('mousedown', (e) => e.stopPropagation());
            frameSlider.addEventListener('click', (e) => e.stopPropagation());

            const frameCounter = document.createElement('span');
            frameCounter.style.minWidth = '45px';
            frameCounter.style.textAlign = 'center';
            frameCounter.style.fontWeight = '500';
            frameCounter.style.fontSize = '13px';
            frameCounter.style.whiteSpace = 'nowrap';
            frameCounter.innerText = '1 / 1';

            const sliderGroup = document.createElement('div');
            sliderGroup.style.display = 'flex';
            sliderGroup.style.alignItems = 'center';
            sliderGroup.style.gap = '6px';
            sliderGroup.style.flex = '1 1 auto';
            sliderGroup.appendChild(frameSlider);
            sliderGroup.appendChild(frameCounter);

            uiContainer.appendChild(btnGroup);
            uiContainer.appendChild(sliderGroup);
            container.appendChild(uiContainer);

            // --- Right Side UI (Container for Top-Right Scrollable Tools & Bottom-Right Info Panel) ---
            const rightSideContainer = document.createElement('div');
            rightSideContainer.style.position = 'absolute';
            rightSideContainer.style.top = '15px';
            rightSideContainer.style.right = '15px';
            rightSideContainer.style.bottom = '15px';
            rightSideContainer.style.zIndex = '10';
            rightSideContainer.style.display = 'flex';
            rightSideContainer.style.flexDirection = 'column';
            rightSideContainer.style.alignItems = 'flex-end';
            rightSideContainer.style.gap = '8px';
            rightSideContainer.style.pointerEvents = 'none';

            // Top-right section containing toolbar buttons and expandable panels (scrolls if space is limited)
            const topRightContainer = document.createElement('div');
            topRightContainer.style.display = 'flex';
            topRightContainer.style.flexDirection = 'column';
            topRightContainer.style.alignItems = 'flex-end';
            topRightContainer.style.gap = '8px';
            topRightContainer.style.pointerEvents = 'none';
            topRightContainer.style.overflowY = 'auto';
            topRightContainer.style.overflowX = 'hidden';
            topRightContainer.style.padding = '0 4px 6px 4px';
            topRightContainer.style.boxSizing = 'border-box';
            topRightContainer.style.flexShrink = '1';
            topRightContainer.style.minHeight = '0';
            topRightContainer.style.scrollbarWidth = 'thin';
            topRightContainer.style.scrollbarColor = 'rgba(0, 0, 0, 0.25) transparent';

            topRightContainer.addEventListener('wheel', (e) => {
                if (topRightContainer.scrollHeight > topRightContainer.clientHeight) {
                    e.stopPropagation();
                }
            }, { passive: true });

            rightSideContainer.appendChild(topRightContainer);

            // --- Atom Info Panel (Stationary at Bottom-Right) ---
            const infoPanel = document.createElement('div');
            infoPanel.id = 'infoPanel';
            infoPanel.style.marginTop = 'auto'; // push to the bottom
            infoPanel.style.pointerEvents = 'auto';
            infoPanel.style.display = 'none'; // hidden by default
            infoPanel.style.background = 'rgba(255, 255, 255, 0.7)';
            infoPanel.style.backdropFilter = 'blur(10px)';
            infoPanel.style.WebkitBackdropFilter = 'blur(10px)';
            infoPanel.style.borderRadius = '8px';
            infoPanel.style.padding = '12px';
            infoPanel.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            infoPanel.style.fontFamily = 'monospace';
            infoPanel.style.fontSize = '12px';
            infoPanel.style.color = '#333';
            infoPanel.style.whiteSpace = 'pre';
            infoPanel.style.flexShrink = '0';
            rightSideContainer.appendChild(infoPanel);

            // Prevent clicks on UI panels from bubbling up and clearing the selection
            uiContainer.addEventListener('click', (e) => e.stopPropagation());
            infoPanel.addEventListener('click', (e) => e.stopPropagation());

            // --- Help Button UI ---
            let isHelpOpen = false;

            const helpContainer = document.createElement('div');
            helpContainer.style.display = model.get('show_help') ? 'flex' : 'none';
            helpContainer.style.flexDirection = 'column';
            helpContainer.style.alignItems = 'flex-end';
            helpContainer.style.pointerEvents = 'auto';

            const helpSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
            const helpBtn = document.createElement('button');
            helpBtn.innerHTML = helpSvg;
            helpBtn.style.color = '#333';
            helpBtn.style.background = 'rgba(255, 255, 255, 0.7)';
            helpBtn.style.border = 'none';
            helpBtn.style.outline = 'none';
            helpBtn.style.backdropFilter = 'blur(10px)';
            helpBtn.style.WebkitBackdropFilter = 'blur(10px)';
            helpBtn.style.borderRadius = '8px';
            helpBtn.style.padding = '8px';
            helpBtn.style.cursor = 'pointer';
            helpBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            helpBtn.style.transition = 'transform 0.2s, background 0.2s, color 0.2s';
            helpBtn.title = 'Help & Controls (H)';

            helpBtn.onmouseover = () => { helpBtn.style.transform = 'scale(1.1)'; if (!isHelpOpen) { helpBtn.style.background = 'rgba(255,255,255,0.9)'; } };
            helpBtn.onmouseout = () => { helpBtn.style.transform = 'scale(1)'; if (!isHelpOpen) { helpBtn.style.background = 'rgba(255,255,255,0.7)'; } };
            helpContainer.appendChild(helpBtn);
            helpContainer.addEventListener('click', (e) => e.stopPropagation());

            // --- Help Overlay Modal ---
            const helpOverlay = document.createElement('div');
            helpOverlay.style.position = 'absolute';
            helpOverlay.style.top = '50%';
            helpOverlay.style.left = '50%';
            helpOverlay.style.transform = 'translate(-50%, -50%)';
            helpOverlay.style.zIndex = '100';
            helpOverlay.style.display = 'none';
            helpOverlay.style.maxHeight = 'calc(100% - 30px)';
            helpOverlay.style.maxWidth = 'calc(100% - 30px)';
            helpOverlay.style.width = '360px';
            helpOverlay.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
            helpOverlay.style.backdropFilter = 'blur(12px)';
            helpOverlay.style.WebkitBackdropFilter = 'blur(12px)';
            helpOverlay.style.borderRadius = '12px';
            helpOverlay.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.2), 0 2px 6px rgba(0, 0, 0, 0.1)';
            helpOverlay.style.border = '1px solid rgba(0, 0, 0, 0.1)';
            helpOverlay.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            helpOverlay.style.fontSize = '13px';
            helpOverlay.style.color = '#222';
            helpOverlay.style.padding = '14px 18px';
            helpOverlay.style.boxSizing = 'border-box';
            helpOverlay.style.overflowY = 'auto';
            helpOverlay.style.pointerEvents = 'auto';
            container.appendChild(helpOverlay);

            helpOverlay.addEventListener('click', (e) => e.stopPropagation());
            helpOverlay.addEventListener('mousedown', (e) => e.stopPropagation());
            helpOverlay.addEventListener('pointerdown', (e) => e.stopPropagation());

            const updateHelpContent = () => {
                const showAxes = model.get('show_axes');
                const measuring = model.get('measuring_tool');
                const frames = model.get('data') || [];
                const isTrajectory = frames.length > 1;
                const cFrame = model.get('current_frame') || 0;
                const fData = isTrajectory ? (frames[cFrame] || {}) : (frames[0] || {});
                const hasExtraData = fData.extra_data && Object.keys(fData.extra_data).length > 0;

                const kbdStyle = 'display:inline-block; padding: 2px 6px; font-family: monospace; font-size: 11px; font-weight: 600; color: #333; background: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 1px 1px rgba(0,0,0,0.1); margin-right: 4px;';
                const sectionTitleStyle = 'font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #666; margin-top: 10px; margin-bottom: 6px; border-bottom: 1px solid rgba(0,0,0,0.06); padding-bottom: 2px;';
                const rowStyle = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;';

                let html = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 8px;">
                        <div style="font-weight: 700; font-size: 15px; display: flex; align-items: center; gap: 6px;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00acc1" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                            <span>Viewer Controls</span>
                        </div>
                        <button id="marimol-help-close-btn" style="background: none; border: none; cursor: pointer; color: #888; font-size: 18px; font-weight: bold; line-height: 1; padding: 2px 6px; border-radius: 4px; transition: color 0.15s, background 0.15s;">✕</button>
                    </div>
                `;

                // Navigation Section
                html += `<div style="${sectionTitleStyle}">Navigation</div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Left Click</span> + Drag</span><span style="color:#555;">Rotate</span></div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Right Click</span> + Drag</span><span style="color:#555;">Pan</span></div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Scroll Wheel</span></span><span style="color:#555;">Zoom</span></div>`;

                // Selection Section
                html += `<div style="${sectionTitleStyle}">Atom Selection</div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Click</span> on Atom</span><span style="color:#555;">Select & Inspect</span></div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Shift</span> + <span style="${kbdStyle}">Click</span></span><span style="color:#555;">Multi-select</span></div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Click</span> Background</span><span style="color:#555;">Deselect</span></div>`;

                // Axis Snapping (Conditional)
                if (showAxes) {
                    html += `<div style="${sectionTitleStyle}">Axis Snapping</div>`;
                    html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Click</span> <span style="color:#ff4444; font-weight:bold;">X</span> / <span style="color:#2e7d32; font-weight:bold;">Y</span> / <span style="color:#1565c0; font-weight:bold;">Z</span></span><span style="color:#555;">Snap view to axis</span></div>`;
                }

                // Measuring Tool (Conditional)
                if (measuring) {
                    html += `<div style="${sectionTitleStyle}">Measuring Tool</div>`;
                    html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Ruler Icon</span></span><span style="color:#555;">Toggle measuring</span></div>`;
                    html += `<div style="${rowStyle}"><span>Click 2 atoms</span><span style="color:#555;">Distance (Å)</span></div>`;
                    html += `<div style="${rowStyle}"><span>Click 3 atoms</span><span style="color:#555;">Angle (°)</span></div>`;
                    html += `<div style="${rowStyle}"><span>Click 4 atoms</span><span style="color:#555;">Dihedral (°)</span></div>`;
                }

                // Trajectory Controls (Conditional)
                if (isTrajectory) {
                    html += `<div style="${sectionTitleStyle}">Trajectory</div>`;
                    html += `<div style="${rowStyle}"><span>Play / Step buttons</span><span style="color:#555;">Playback frames</span></div>`;
                    if (model.get('trajectory_slider')) {
                        html += `<div style="${rowStyle}"><span>Slider</span><span style="color:#555;">Scrub frames</span></div>`;
                    }
                }

                // Extra Data (Conditional)
                if (hasExtraData) {
                    html += `<div style="${sectionTitleStyle}">Structure Info</div>`;
                    html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">List Icon</span></span><span style="color:#555;">Toggle metadata</span></div>`;
                }

                // Capture & Recording (Conditional)
                if (model.get('recording_tools')) {
                    html += `<div style="${sectionTitleStyle}">Capture & Recording</div>`;
                    html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Camera</span> / <span style="${kbdStyle}">S</span></span><span style="color:#555;">Screenshot (PNG)</span></div>`;
                    html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Video</span> / <span style="${kbdStyle}">R</span></span><span style="color:#555;">Record Animation</span></div>`;
                }

                // Keyboard Shortcuts
                html += `<div style="${sectionTitleStyle}">Shortcuts</div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">H</span></span><span style="color:#555;">Toggle help overlay</span></div>`;
                html += `<div style="${rowStyle}"><span><span style="${kbdStyle}">Esc</span></span><span style="color:#555;">Close help</span></div>`;

                helpOverlay.innerHTML = html;

                const closeBtn = helpOverlay.querySelector('#marimol-help-close-btn');
                if (closeBtn) {
                    closeBtn.onclick = () => toggleHelp(false);
                    closeBtn.onmouseover = () => { closeBtn.style.color = '#000'; closeBtn.style.background = 'rgba(0,0,0,0.06)'; };
                    closeBtn.onmouseout = () => { closeBtn.style.color = '#888'; closeBtn.style.background = 'none'; };
                }
            };

            const toggleHelp = (forceState) => {
                if (!model.get('show_help')) {
                    isHelpOpen = false;
                    helpOverlay.style.display = 'none';
                    helpBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                    helpBtn.style.color = '#333';
                    return;
                }
                isHelpOpen = (typeof forceState === 'boolean') ? forceState : !isHelpOpen;
                if (isHelpOpen) {
                    updateHelpContent();
                    helpOverlay.style.display = 'block';
                    helpBtn.style.background = '#00acc1';
                    helpBtn.style.color = 'white';
                } else {
                    helpOverlay.style.display = 'none';
                    helpBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                    helpBtn.style.color = '#333';
                }
            };

            helpBtn.addEventListener('click', () => {
                toggleHelp();
            });

            // --- Screenshot & Animation Recording UI ---
            const captureContainer = document.createElement('div');
            captureContainer.style.display = model.get('recording_tools') ? 'flex' : 'none';
            captureContainer.style.flexDirection = 'column';
            captureContainer.style.alignItems = 'flex-end';
            captureContainer.style.pointerEvents = 'auto';
            captureContainer.style.gap = '8px';

            const cameraSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>`;
            const screenshotBtn = document.createElement('button');
            screenshotBtn.innerHTML = cameraSvg;
            screenshotBtn.style.color = '#333';
            screenshotBtn.style.background = 'rgba(255, 255, 255, 0.7)';
            screenshotBtn.style.border = 'none';
            screenshotBtn.style.outline = 'none';
            screenshotBtn.style.backdropFilter = 'blur(10px)';
            screenshotBtn.style.WebkitBackdropFilter = 'blur(10px)';
            screenshotBtn.style.borderRadius = '8px';
            screenshotBtn.style.padding = '8px';
            screenshotBtn.style.cursor = 'pointer';
            screenshotBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            screenshotBtn.style.transition = 'transform 0.2s, background 0.2s';
            screenshotBtn.title = 'Capture Screenshot (PNG)';

            screenshotBtn.onmouseover = () => { screenshotBtn.style.transform = 'scale(1.1)'; screenshotBtn.style.background = 'rgba(255,255,255,0.9)'; };
            screenshotBtn.onmouseout = () => { screenshotBtn.style.transform = 'scale(1)'; screenshotBtn.style.background = 'rgba(255,255,255,0.7)'; };

            const videoSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>`;
            const stopSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="display:block;"><rect x="6" y="6" width="12" height="12" rx="2"></rect></svg>`;

            const recordBtn = document.createElement('button');
            recordBtn.innerHTML = videoSvg;
            recordBtn.style.color = '#333';
            recordBtn.style.background = 'rgba(255, 255, 255, 0.7)';
            recordBtn.style.border = 'none';
            recordBtn.style.outline = 'none';
            recordBtn.style.backdropFilter = 'blur(10px)';
            recordBtn.style.WebkitBackdropFilter = 'blur(10px)';
            recordBtn.style.borderRadius = '8px';
            recordBtn.style.padding = '8px';
            recordBtn.style.cursor = 'pointer';
            recordBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            recordBtn.style.transition = 'transform 0.2s, background 0.2s';
            recordBtn.title = 'Record Animation (WebM/MP4)';

            let isRecording = false;

            recordBtn.onmouseover = () => { recordBtn.style.transform = 'scale(1.1)'; if (!isRecording) { recordBtn.style.background = 'rgba(255,255,255,0.9)'; } };
            recordBtn.onmouseout = () => { recordBtn.style.transform = 'scale(1)'; if (!isRecording) { recordBtn.style.background = 'rgba(255,255,255,0.7)'; } };

            const recordingBadge = document.createElement('div');
            recordingBadge.style.display = 'none';
            recordingBadge.style.padding = '4px 8px';
            recordingBadge.style.background = 'rgba(229, 57, 53, 0.85)';
            recordingBadge.style.backdropFilter = 'blur(10px)';
            recordingBadge.style.WebkitBackdropFilter = 'blur(10px)';
            recordingBadge.style.borderRadius = '6px';
            recordingBadge.style.fontFamily = 'monospace';
            recordingBadge.style.fontSize = '11px';
            recordingBadge.style.fontWeight = 'bold';
            recordingBadge.style.color = 'white';
            recordingBadge.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
            recordingBadge.style.whiteSpace = 'nowrap';
            recordingBadge.innerText = '● REC 00:00';

            captureContainer.appendChild(screenshotBtn);
            captureContainer.appendChild(recordBtn);
            captureContainer.appendChild(recordingBadge);
            captureContainer.addEventListener('click', (e) => e.stopPropagation());

            let recordCanvas = null;
            let recordCtx = null;

            const drawDomNode = (ctx, node, containerRect, scale) => {
                if (!node || node.nodeType !== Node.ELEMENT_NODE) return;
                const style = window.getComputedStyle ? window.getComputedStyle(node) : node.style;
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return;

                const rect = node.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) return;

                const x = Math.round((rect.left - containerRect.left) * scale);
                const y = Math.round((rect.top - containerRect.top) * scale);
                const w = Math.round(rect.width * scale);
                const h = Math.round(rect.height * scale);

                const tag = node.tagName ? node.tagName.toLowerCase() : '';

                ctx.save();

                // 1. Draw background & borders if any
                const bg = style.backgroundColor;
                const hasBg = bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)';
                const borderRadius = parseFloat(style.borderRadius) || 0;
                const r = Math.round(borderRadius * scale);

                if (hasBg) {
                    const shadow = style.boxShadow;
                    const hasShadow = shadow && shadow !== 'none' && !shadow.includes('none');
                    if (hasShadow) {
                        ctx.save();
                        ctx.fillStyle = 'rgba(0, 0, 0, 0.04)';
                        ctx.beginPath();
                        if (r > 0 && typeof ctx.roundRect === 'function') {
                            ctx.roundRect(x - 1 * scale, y + 1 * scale, w + 2 * scale, h + 3 * scale, r + 1 * scale);
                        } else {
                            ctx.rect(x - 1 * scale, y + 1 * scale, w + 2 * scale, h + 3 * scale);
                        }
                        ctx.fill();

                        ctx.fillStyle = 'rgba(0, 0, 0, 0.06)';
                        ctx.beginPath();
                        if (r > 0 && typeof ctx.roundRect === 'function') {
                            ctx.roundRect(x, y + 2 * scale, w, h + 2 * scale, r);
                        } else {
                            ctx.rect(x, y + 2 * scale, w, h + 2 * scale);
                        }
                        ctx.fill();
                        ctx.restore();
                    }

                    ctx.fillStyle = bg;
                    ctx.beginPath();
                    if (r > 0 && typeof ctx.roundRect === 'function') {
                        ctx.roundRect(x, y, w, h, r);
                    } else if (r > 0) {
                        const radius = Math.min(r, w / 2, h / 2);
                        ctx.moveTo(x + radius, y);
                        ctx.arcTo(x + w, y, x + w, y + h, radius);
                        ctx.arcTo(x + w, y + h, x, y + h, radius);
                        ctx.arcTo(x, y + h, x, y, radius);
                        ctx.arcTo(x, y, x + w, y, radius);
                        ctx.closePath();
                    } else {
                        ctx.rect(x, y, w, h);
                    }
                    ctx.fill();

                    // Subtle glassmorphism border ring so white buttons on white backgrounds are clearly defined!
                    ctx.lineWidth = Math.max(1, 1 * scale);
                    ctx.strokeStyle = 'rgba(0, 0, 0, 0.08)';
                    ctx.stroke();
                }

                // Border (exclude buttons, SVGs, and transparent borders)
                const borderStyle = style.borderStyle;
                const hasBorder = borderStyle && borderStyle !== 'none' && borderStyle !== 'hidden';
                const borderWidth = parseFloat(style.borderTopWidth || style.borderWidth) || 0;
                const borderColor = style.borderTopColor || style.borderColor;
                if (tag !== 'button' && tag !== 'svg' && hasBorder && borderWidth > 0 && borderColor && borderColor !== 'transparent') {
                    ctx.lineWidth = borderWidth * scale;
                    ctx.strokeStyle = borderColor;
                    ctx.beginPath();
                    if (r > 0 && typeof ctx.roundRect === 'function') {
                        ctx.roundRect(x, y, w, h, r);
                    } else if (r > 0) {
                        const radius = Math.min(r, w / 2, h / 2);
                        ctx.moveTo(x + radius, y);
                        ctx.arcTo(x + w, y, x + w, y + h, radius);
                        ctx.arcTo(x + w, y + h, x, y + h, radius);
                        ctx.arcTo(x, y + h, x, y, radius);
                        ctx.arcTo(x, y, x + w, y, radius);
                        ctx.closePath();
                    } else {
                        ctx.rect(x, y, w, h);
                    }
                    ctx.stroke();
                }

                // 2. If SVG element, draw its vector paths in unified SVG coordinate space
                if (node.tagName && node.tagName.toLowerCase() === 'svg') {
                    const resolveColor = (col) => {
                        if (!col || col === 'none' || col === 'transparent') return 'none';
                        if (col === 'currentColor') return style.color || '#333333';
                        return col;
                    };

                    const nodeFill = node.getAttribute('fill') || (style.fill && style.fill !== 'none' ? style.fill : (node.getAttribute('stroke') ? 'none' : 'currentColor'));
                    const nodeStroke = node.getAttribute('stroke') || (style.stroke && style.stroke !== 'none' ? style.stroke : 'none');
                    const nodeStrokeWidth = parseFloat(node.getAttribute('stroke-width')) || parseFloat(style.strokeWidth) || 0;

                    const viewBox = node.getAttribute('viewBox');
                    let vbW = 24, vbH = 24;
                    if (viewBox) {
                        const parts = viewBox.trim().split(/[\\s,]+/).map(Number);
                        if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
                            vbW = parts[2];
                            vbH = parts[3];
                        }
                    }

                    const svgScaleX = w / vbW;
                    const svgScaleY = h / vbH;

                    for (let child of node.children) {
                        const cTag = child.tagName ? child.tagName.toLowerCase() : '';
                        const fillAttr = child.getAttribute('fill') || nodeFill;
                        const strokeAttr = child.getAttribute('stroke') || nodeStroke;
                        const strokeWidthAttr = parseFloat(child.getAttribute('stroke-width')) || nodeStrokeWidth;

                        const resolvedFill = resolveColor(fillAttr);
                        const resolvedStroke = resolveColor(strokeAttr);

                        ctx.save();
                        // Transform context to match SVG viewBox coordinates exactly
                        ctx.translate(x, y);
                        ctx.scale(svgScaleX, svgScaleY);

                        if (resolvedFill !== 'none') {
                            ctx.fillStyle = resolvedFill;
                        }
                        if (resolvedStroke !== 'none' && strokeWidthAttr > 0) {
                            ctx.strokeStyle = resolvedStroke;
                            ctx.lineWidth = strokeWidthAttr;
                            ctx.lineCap = child.getAttribute('stroke-linecap') || node.getAttribute('stroke-linecap') || 'round';
                            ctx.lineJoin = child.getAttribute('stroke-linejoin') || node.getAttribute('stroke-linejoin') || 'round';
                        }

                        if (cTag === 'path') {
                            const d = child.getAttribute('d');
                            if (d) {
                                const path = new Path2D(d);
                                if (resolvedFill !== 'none') ctx.fill(path);
                                if (resolvedStroke !== 'none' && strokeWidthAttr > 0) ctx.stroke(path);
                            }
                        } else if (cTag === 'circle') {
                            const cx = parseFloat(child.getAttribute('cx')) || 0;
                            const cy = parseFloat(child.getAttribute('cy')) || 0;
                            const cr = parseFloat(child.getAttribute('r')) || 0;
                            ctx.beginPath();
                            ctx.arc(cx, cy, cr, 0, Math.PI * 2);
                            if (resolvedFill !== 'none') ctx.fill();
                            if (resolvedStroke !== 'none' && strokeWidthAttr > 0) ctx.stroke();
                        } else if (cTag === 'rect') {
                            const rx = parseFloat(child.getAttribute('x')) || 0;
                            const ry = parseFloat(child.getAttribute('y')) || 0;
                            const rw = parseFloat(child.getAttribute('width')) || 0;
                            const rh = parseFloat(child.getAttribute('height')) || 0;
                            const rRadius = parseFloat(child.getAttribute('rx')) || 0;
                            ctx.beginPath();
                            if (rRadius > 0 && typeof ctx.roundRect === 'function') {
                                ctx.roundRect(rx, ry, rw, rh, rRadius);
                            } else {
                                ctx.rect(rx, ry, rw, rh);
                            }
                            if (resolvedFill !== 'none') ctx.fill();
                            if (resolvedStroke !== 'none' && strokeWidthAttr > 0) ctx.stroke();
                        } else if (cTag === 'polygon') {
                            const pointsStr = child.getAttribute('points');
                            if (pointsStr) {
                                const pts = pointsStr.trim().split(/[\\s,]+/).map(Number);
                                ctx.beginPath();
                                for (let i = 0; i < pts.length; i += 2) {
                                    if (i === 0) ctx.moveTo(pts[i], pts[i + 1]);
                                    else ctx.lineTo(pts[i], pts[i + 1]);
                                }
                                ctx.closePath();
                                if (resolvedFill !== 'none') ctx.fill();
                                if (resolvedStroke !== 'none' && strokeWidthAttr > 0) ctx.stroke();
                            }
                        } else if (cTag === 'line') {
                            const x1 = parseFloat(child.getAttribute('x1')) || 0;
                            const y1 = parseFloat(child.getAttribute('y1')) || 0;
                            const x2 = parseFloat(child.getAttribute('x2')) || 0;
                            const y2 = parseFloat(child.getAttribute('y2')) || 0;
                            ctx.beginPath();
                            ctx.moveTo(x1, y1);
                            ctx.lineTo(x2, y2);
                            if (resolvedStroke !== 'none' && strokeWidthAttr > 0) ctx.stroke();
                        }
                        ctx.restore();
                    }
                    ctx.restore();
                    return;
                }

                // 3. If input[type="range"], draw the scrubber track and thumb
                if (node.tagName && node.tagName.toLowerCase() === 'input' && node.type === 'range') {
                    const min = parseFloat(node.min) || 0;
                    const max = parseFloat(node.max) || 0;
                    const val = parseFloat(node.value) || 0;
                    const ratio = max > min ? (val - min) / (max - min) : 0;

                    const trackY = y + h / 2;
                    const trackH = Math.max(2 * scale, 3);
                    ctx.fillStyle = '#cccccc';
                    ctx.beginPath();
                    if (typeof ctx.roundRect === 'function') {
                        ctx.roundRect(x, trackY - trackH / 2, w, trackH, trackH / 2);
                    } else {
                        ctx.rect(x, trackY - trackH / 2, w, trackH);
                    }
                    ctx.fill();

                    const thumbRadius = Math.max(4 * scale, 6);
                    const thumbX = x + ratio * w;
                    ctx.fillStyle = '#555555';
                    ctx.beginPath();
                    ctx.arc(thumbX, trackY, thumbRadius, 0, Math.PI * 2);
                    ctx.fill();

                    ctx.restore();
                    return;
                }

                // 4. Text nodes (handles pure text elements and mixed text nodes)
                for (const child of node.childNodes) {
                    if (child.nodeType === Node.TEXT_NODE) {
                        const rawText = child.nodeValue;
                        if (rawText && rawText.trim().length > 0) {
                            const range = document.createRange();
                            range.selectNode(child);
                            const tr = range.getBoundingClientRect();
                            if (tr.width > 0 && tr.height > 0) {
                                const tx = Math.round((tr.left - containerRect.left) * scale);
                                const ty = Math.round((tr.top - containerRect.top) * scale);
                                const th = Math.round(tr.height * scale);

                                const fontSize = Math.max(10, Math.round((parseFloat(style.fontSize) || 13) * scale));
                                const isMono = (style.fontFamily && style.fontFamily.includes('mono')) || (node.id === 'infoPanel');
                                const fontFam = isMono ? 'monospace' : 'system-ui, -apple-system, sans-serif';
                                const fontWeight = style.fontWeight && style.fontWeight !== '400' ? style.fontWeight : 'normal';
                                ctx.font = `${fontWeight} ${fontSize}px ${fontFam}`;
                                ctx.fillStyle = style.color || '#333333';
                                ctx.textBaseline = 'middle';
                                ctx.textAlign = 'left';

                                const textShadow = style.textShadow;
                                const hasWhiteOutline = textShadow && textShadow.includes('#fff');
                                if (hasWhiteOutline) {
                                    ctx.save();
                                    ctx.strokeStyle = '#ffffff';
                                    ctx.lineWidth = 3 * scale;
                                    ctx.strokeText(rawText.trim(), tx, ty + th / 2);
                                    ctx.restore();
                                }
                                ctx.fillText(rawText.trim(), tx, ty + th / 2);
                            }
                        }
                    }
                }

                ctx.restore();

                const overflow = style.overflow || '';
                const overflowY = style.overflowY || '';
                const shouldClip = (overflow === 'hidden' || overflow === 'auto' || overflowY === 'hidden' || overflowY === 'auto');
                if (shouldClip) {
                    ctx.save();
                    ctx.beginPath();
                    ctx.rect(x, y, w, h);
                    ctx.clip();
                }

                for (let child of node.children) {
                    drawDomNode(ctx, child, containerRect, scale);
                }

                if (shouldClip) {
                    ctx.restore();
                }
            };

            const drawOverlaysToCanvas = (ctx, scale = 1) => {
                const containerRect = container.getBoundingClientRect();
                const overlays = [labelsContainer, uiContainer, rightSideContainer, helpOverlay];
                for (const el of overlays) {
                    if (el) {
                        drawDomNode(ctx, el, containerRect, scale);
                    }
                }
            };

            const captureScreenshot = async (defaultName = 'marimol_structure.png') => {
                if (document.activeElement && typeof document.activeElement.blur === 'function') {
                    document.activeElement.blur();
                }
                screenshotBtn.style.transform = 'scale(1)';
                screenshotBtn.style.background = 'rgba(255, 255, 255, 0.7)';

                const dpi = model.get('dpi') || 200;
                const scale = Math.max(0.5, Math.min(8.0, dpi / 96.0));
                const origWidth = container.clientWidth;
                const origHeight = container.clientHeight;
                const targetWidth = Math.round(origWidth * scale);
                const targetHeight = Math.round(origHeight * scale);
                const origPixelRatio = renderer.getPixelRatio();

                // Trigger native file picker synchronously while user gesture is active
                let fileHandlePromise = null;
                if (typeof window.showSaveFilePicker === 'function') {
                    try {
                        fileHandlePromise = window.showSaveFilePicker({
                            suggestedName: defaultName,
                            types: [{
                                description: 'PNG Image (*.png)',
                                accept: { 'image/png': ['.png'] },
                            }],
                        });
                    } catch (err) {
                        console.warn('showSaveFilePicker synchronous error:', err);
                    }
                }

                // Render high-DPI frame
                renderer.setPixelRatio(1);
                renderer.setSize(targetWidth, targetHeight, false);

                if (camera.isPerspectiveCamera) {
                    camera.aspect = targetWidth / targetHeight;
                    camera.updateProjectionMatrix();
                }

                renderer.setViewport(0, 0, targetWidth, targetHeight);
                renderer.clear();
                renderer.render(scene, camera);

                if (model.get('show_axes')) {
                    axesCamera.position.copy(camera.position).sub(controls.target).normalize().multiplyScalar(4);
                    axesCamera.quaternion.copy(camera.quaternion);
                    renderer.clearDepth();
                    const axesSize = Math.round(80 * scale);
                    const axesMargin = Math.round(10 * scale);
                    renderer.setViewport(axesMargin, axesMargin, axesSize, axesSize);
                    renderer.render(axesScene, axesCamera);
                }

                const includeBgd = model.get('record_include_bgd');
                const includeUi = model.get('record_include_ui');

                let blobPromise;
                if (!includeBgd && !includeUi) {
                    blobPromise = new Promise((resolve) => {
                        renderer.domElement.toBlob(resolve, 'image/png');
                    });
                } else {
                    const exportCanvas = document.createElement('canvas');
                    exportCanvas.width = targetWidth;
                    exportCanvas.height = targetHeight;
                    const ctx = exportCanvas.getContext('2d');

                    if (includeBgd) {
                        ctx.fillStyle = model.get('background_color') || '#ffffff';
                        ctx.fillRect(0, 0, targetWidth, targetHeight);
                    }

                    ctx.drawImage(renderer.domElement, 0, 0, targetWidth, targetHeight);

                    if (includeUi) {
                        drawOverlaysToCanvas(ctx, scale);
                    }

                    blobPromise = new Promise((resolve) => {
                        exportCanvas.toBlob(resolve, 'image/png');
                    });
                }

                // Restore live renderer dimensions
                renderer.setPixelRatio(origPixelRatio);
                renderer.setSize(origWidth, origHeight);
                if (camera.isPerspectiveCamera) {
                    camera.aspect = origWidth / origHeight;
                    camera.updateProjectionMatrix();
                }

                try {
                    let fileHandle = null;
                    if (fileHandlePromise) {
                        try {
                            fileHandle = await fileHandlePromise;
                        } catch (err) {
                            if (err && err.name === 'AbortError') return; // User cancelled
                            console.warn('showSaveFilePicker rejected or unsupported:', err);
                        }
                    }

                    const blob = await blobPromise;
                    if (!blob) return;

                    if (fileHandle) {
                        const writable = await fileHandle.createWritable();
                        await writable.write(blob);
                        await writable.close();
                        return;
                    }

                    // Direct browser download without blocking prompts
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = defaultName;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(() => URL.revokeObjectURL(url), 5000);
                } catch (err) {
                    console.error('Error saving screenshot:', err);
                }
            };

            screenshotBtn.addEventListener('click', () => {
                captureScreenshot();
            });

            let mediaRecorder = null;
            let recordedChunks = [];
            let recordTimerInterval = null;
            let recordSeconds = 0;
            let origPixelRatioBeforeRecord = 1;

            const getSupportedMimeType = () => {
                const types = [
                    'video/webm;codecs=vp9',
                    'video/webm;codecs=vp8',
                    'video/webm',
                    'video/mp4'
                ];
                for (const t of types) {
                    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) return t;
                }
                return '';
            };

            const startRecording = () => {
                if (isRecording) return;
                const fps = model.get('traj_fps') || 30;
                const dpi = model.get('dpi') || 200;
                const targetPixelRatio = Math.max(1.0, Math.min(3.0, dpi / 96.0));
                origPixelRatioBeforeRecord = renderer.getPixelRatio();
                renderer.setPixelRatio(targetPixelRatio);
                renderer.setSize(container.clientWidth, container.clientHeight);

                const includeBgd = model.get('record_include_bgd');
                const includeUi = model.get('record_include_ui');

                let stream = null;
                if (includeBgd || includeUi) {
                    recordCanvas = document.createElement('canvas');
                    recordCanvas.width = renderer.domElement.width;
                    recordCanvas.height = renderer.domElement.height;
                    recordCanvas.style.position = 'fixed';
                    recordCanvas.style.top = '-9999px';
                    recordCanvas.style.left = '-9999px';
                    recordCanvas.style.width = '1px';
                    recordCanvas.style.height = '1px';
                    recordCanvas.style.opacity = '0';
                    recordCanvas.style.pointerEvents = 'none';
                    document.body.appendChild(recordCanvas);

                    recordCtx = recordCanvas.getContext('2d');
                    if (includeBgd) {
                        recordCtx.fillStyle = model.get('background_color') || '#ffffff';
                        recordCtx.fillRect(0, 0, recordCanvas.width, recordCanvas.height);
                    }
                    recordCtx.drawImage(renderer.domElement, 0, 0);
                    if (includeUi) {
                        drawOverlaysToCanvas(recordCtx, targetPixelRatio);
                    }
                    stream = recordCanvas.captureStream ? recordCanvas.captureStream(Math.max(15, Math.min(60, fps))) : null;
                } else {
                    stream = renderer.domElement.captureStream ? renderer.domElement.captureStream(Math.max(15, Math.min(60, fps))) : null;
                }

                if (!stream) {
                    console.warn('HTMLCanvasElement.captureStream is not supported in this browser.');
                    renderer.setPixelRatio(origPixelRatioBeforeRecord);
                    renderer.setSize(container.clientWidth, container.clientHeight);
                    if (recordCanvas && recordCanvas.parentNode) {
                        recordCanvas.parentNode.removeChild(recordCanvas);
                    }
                    recordCanvas = null;
                    recordCtx = null;
                    return;
                }

                recordedChunks = [];
                const mimeType = getSupportedMimeType();
                const options = mimeType ? { mimeType } : {};

                try {
                    mediaRecorder = new MediaRecorder(stream, options);
                } catch (err) {
                    console.warn('Could not initialize MediaRecorder:', err);
                    renderer.setPixelRatio(origPixelRatioBeforeRecord);
                    renderer.setSize(container.clientWidth, container.clientHeight);
                    if (recordCanvas && recordCanvas.parentNode) {
                        recordCanvas.parentNode.removeChild(recordCanvas);
                    }
                    recordCanvas = null;
                    recordCtx = null;
                    return;
                }

                mediaRecorder.ondataavailable = (e) => {
                    if (e.data && e.data.size > 0) {
                        recordedChunks.push(e.data);
                    }
                };

                mediaRecorder.start(100);
                isRecording = true;
                recordBtn.innerHTML = stopSvg;
                recordBtn.style.background = '#e53935';
                recordBtn.style.color = 'white';
                recordBtn.title = 'Stop Recording';
                recordingBadge.style.display = 'flex';
                recordSeconds = 0;
                recordingBadge.innerText = '● REC 00:00';
                recordTimerInterval = setInterval(() => {
                    recordSeconds++;
                    const mins = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
                    const secs = String(recordSeconds % 60).padStart(2, '0');
                    recordingBadge.innerText = `● REC ${mins}:${secs}`;
                }, 1000);

                const frames = model.get('data') || [];
                const multiTraj = model.get('multi_traj') !== false;
                if (frames.length > 1 && multiTraj && !isPlaying) {
                    setFrame(0);
                    togglePlay();
                }
            };

            const stopRecording = async () => {
                if (!isRecording) return;
                isRecording = false;
                if (recordTimerInterval) {
                    clearInterval(recordTimerInterval);
                    recordTimerInterval = null;
                }
                recordingBadge.style.display = 'none';
                recordBtn.innerHTML = videoSvg;
                recordBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                recordBtn.style.color = '#333';
                recordBtn.title = 'Record Animation (WebM/MP4)';

                const rawType = (mediaRecorder && mediaRecorder.mimeType) || getSupportedMimeType() || 'video/webm';
                const pureMime = rawType.split(';')[0].trim() || 'video/webm';
                const ext = pureMime.includes('mp4') ? 'mp4' : 'webm';
                const desc = ext === 'mp4' ? 'MP4 Video (*.mp4)' : 'WebM Video (*.webm)';
                const defaultName = `marimol_animation.${ext}`;

                // Trigger native file picker synchronously during user gesture if supported
                let fileHandlePromise = null;
                if (typeof window.showSaveFilePicker === 'function') {
                    try {
                        fileHandlePromise = window.showSaveFilePicker({
                            suggestedName: defaultName,
                            types: [{
                                description: desc,
                                accept: { [pureMime]: [`.${ext}`] },
                            }],
                        });
                    } catch (err) {
                        console.warn('showSaveFilePicker synchronous error:', err);
                    }
                }

                // Stop recorder and collect final blob
                const blobPromise = new Promise((resolve) => {
                    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                        resolve(new Blob(recordedChunks, { type: rawType }));
                    } else {
                        mediaRecorder.onstop = () => {
                            resolve(new Blob(recordedChunks, { type: rawType }));
                        };
                        mediaRecorder.stop();
                    }
                });

                try {
                    let fileHandle = null;
                    if (fileHandlePromise) {
                        try {
                            fileHandle = await fileHandlePromise;
                        } catch (err) {
                            if (err && err.name === 'AbortError') {
                                return; // User explicitly cancelled file picker dialog
                            }
                            console.warn('showSaveFilePicker rejected or blocked:', err);
                        }
                    }

                    const blob = await blobPromise;
                    if (!blob || blob.size === 0) return;

                    if (fileHandle) {
                        const writable = await fileHandle.createWritable();
                        await writable.write(blob);
                        await writable.close();
                        return;
                    }

                    // Direct automatic download
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = defaultName;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(() => URL.revokeObjectURL(url), 5000);
                } catch (err) {
                    console.error('Error saving recorded animation:', err);
                } finally {
                    renderer.setPixelRatio(origPixelRatioBeforeRecord || window.devicePixelRatio || 1);
                    renderer.setSize(container.clientWidth, container.clientHeight);
                    if (recordCanvas && recordCanvas.parentNode) {
                        recordCanvas.parentNode.removeChild(recordCanvas);
                    }
                    recordCanvas = null;
                    recordCtx = null;
                }
            };

            const toggleRecording = () => {
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            };

            recordBtn.addEventListener('click', () => {
                toggleRecording();
            });

            // --- Measuring Tool UI ---
            let isMeasuring = false;
            let measureSelection = []; // array of {index, pos: THREE.Vector3}
            let measureLineMesh = null;
            let measureSpheres = [];

            const measureContainer = document.createElement('div');
            measureContainer.style.display = 'flex';
            measureContainer.style.flexDirection = 'column';
            measureContainer.style.alignItems = 'flex-end';
            measureContainer.style.pointerEvents = 'auto';

            const rulerSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><rect x="2" y="6" width="20" height="12" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6" y2="10"></line><line x1="10" y1="6" x2="10" y2="10"></line><line x1="14" y1="6" x2="14" y2="10"></line><line x1="18" y1="6" x2="18" y2="10"></line></svg>`;
            const measureBtn = document.createElement('button');
            measureBtn.innerHTML = rulerSvg;
            measureBtn.style.color = '#333';
            measureBtn.style.background = 'rgba(255, 255, 255, 0.7)';
            measureBtn.style.border = 'none';
            measureBtn.style.outline = 'none';
            measureBtn.style.backdropFilter = 'blur(10px)';
            measureBtn.style.WebkitBackdropFilter = 'blur(10px)';
            measureBtn.style.borderRadius = '8px';
            measureBtn.style.padding = '8px';
            measureBtn.style.cursor = 'pointer';
            measureBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            measureBtn.style.transition = 'transform 0.2s, background 0.2s, color 0.2s';
            measureBtn.title = 'Measure Tool (Distance, Angle, Dihedral)';
            measureBtn.onmouseover = () => { measureBtn.style.transform = 'scale(1.1)'; if (!isMeasuring) { measureBtn.style.background = 'rgba(255,255,255,0.9)'; } };
            measureBtn.onmouseout = () => { measureBtn.style.transform = 'scale(1)'; if (!isMeasuring) { measureBtn.style.background = 'rgba(255,255,255,0.7)'; } };

            const measureLabel = document.createElement('div');
            measureLabel.style.marginTop = '8px';
            measureLabel.style.padding = '8px 12px';
            measureLabel.style.background = 'rgba(255, 255, 255, 0.7)';
            measureLabel.style.backdropFilter = 'blur(10px)';
            measureLabel.style.WebkitBackdropFilter = 'blur(10px)';
            measureLabel.style.borderRadius = '8px';
            measureLabel.style.fontFamily = 'monospace';
            measureLabel.style.fontSize = '14px';
            measureLabel.style.fontWeight = 'bold';
            measureLabel.style.color = '#e91e63';
            measureLabel.style.display = 'none';
            measureLabel.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';

            measureContainer.appendChild(measureBtn);
            measureContainer.appendChild(measureLabel);
            // rightSideContainer.insertBefore handles appending measureContainer later
            measureContainer.addEventListener('click', (e) => e.stopPropagation());

            // --- Extra Data UI ---
            const extraDataContainer = document.createElement('div');
            extraDataContainer.style.display = 'none'; // Will be set to flex if data is present
            extraDataContainer.style.flexDirection = 'column';
            extraDataContainer.style.alignItems = 'flex-end';
            extraDataContainer.style.pointerEvents = 'auto';

            const extraDataBtn = document.createElement('button');
            const listSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>`;
            extraDataBtn.innerHTML = listSvg;
            extraDataBtn.style.color = '#333';
            extraDataBtn.style.background = 'rgba(255, 255, 255, 0.7)';
            extraDataBtn.style.border = 'none';
            extraDataBtn.style.outline = 'none';
            extraDataBtn.style.backdropFilter = 'blur(10px)';
            extraDataBtn.style.WebkitBackdropFilter = 'blur(10px)';
            extraDataBtn.style.borderRadius = '8px';
            extraDataBtn.style.padding = '8px';
            extraDataBtn.style.cursor = 'pointer';
            extraDataBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            extraDataBtn.style.transition = 'transform 0.2s, background 0.2s, color 0.2s';
            extraDataBtn.title = 'Toggle Extra Data';

            let isExtraDataOpen = false;

            extraDataBtn.onmouseover = () => { extraDataBtn.style.transform = 'scale(1.1)'; if (!isExtraDataOpen) { extraDataBtn.style.background = 'rgba(255,255,255,0.9)'; } };
            extraDataBtn.onmouseout = () => { extraDataBtn.style.transform = 'scale(1)'; if (!isExtraDataOpen) { extraDataBtn.style.background = 'rgba(255,255,255,0.7)'; } };

            const extraDataPanel = document.createElement('div');
            extraDataPanel.style.marginTop = '8px';
            extraDataPanel.style.marginBottom = '4px';
            extraDataPanel.style.padding = '12px';
            extraDataPanel.style.background = 'rgba(255, 255, 255, 0.7)';
            extraDataPanel.style.backdropFilter = 'blur(10px)';
            extraDataPanel.style.WebkitBackdropFilter = 'blur(10px)';
            extraDataPanel.style.borderRadius = '8px';
            extraDataPanel.style.fontFamily = 'sans-serif';
            extraDataPanel.style.fontSize = '13px';
            extraDataPanel.style.color = '#333';
            extraDataPanel.style.display = 'none';
            extraDataPanel.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            extraDataPanel.style.flexShrink = '0';

            extraDataContainer.appendChild(extraDataBtn);
            extraDataContainer.appendChild(extraDataPanel);

            topRightContainer.appendChild(helpContainer);
            topRightContainer.appendChild(captureContainer);
            topRightContainer.appendChild(measureContainer);
            topRightContainer.appendChild(extraDataContainer);
            container.appendChild(rightSideContainer);

            extraDataContainer.addEventListener('click', (e) => e.stopPropagation());

            extraDataBtn.addEventListener('click', () => {
                isExtraDataOpen = !isExtraDataOpen;
                if (isExtraDataOpen) {
                    extraDataBtn.style.background = '#00acc1';
                    extraDataBtn.style.color = 'white';
                    extraDataPanel.style.display = 'block';
                } else {
                    extraDataBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                    extraDataBtn.style.color = '#333';
                    extraDataPanel.style.display = 'none';
                }
            });

            // Listen to traitlet
            measureContainer.style.display = model.get('measuring_tool') ? 'flex' : 'none';
            model.on('change:measuring_tool', () => {
                const show = model.get('measuring_tool');
                measureContainer.style.display = show ? 'flex' : 'none';
                if (!show && isMeasuring) {
                    measureBtn.click(); // toggle off
                }
                if (isHelpOpen) updateHelpContent();
            });

            function clearMeasurement() {
                measureSelection = [];
                if (measureLineMesh) {
                    scene.remove(measureLineMesh);
                    measureLineMesh.geometry.dispose();
                    measureLineMesh.material.dispose();
                    measureLineMesh = null;
                }
                measureSpheres.forEach(mesh => {
                    scene.remove(mesh);
                    mesh.geometry.dispose();
                    mesh.material.dispose();
                });
                measureSpheres = [];
                measureLabel.style.display = 'none';
                measureLabel.innerText = '';
            }

            function updateMeasurementUI() {
                if (measureLineMesh) {
                    scene.remove(measureLineMesh);
                    measureLineMesh.geometry.dispose();
                    measureLineMesh.material.dispose();
                    measureLineMesh = null;
                }
                measureSpheres.forEach(mesh => {
                    scene.remove(mesh);
                    mesh.geometry.dispose();
                    mesh.material.dispose();
                });
                measureSpheres = [];

                if (measureSelection.length === 0) {
                    if (isMeasuring) {
                        measureLabel.style.display = 'block';
                        measureLabel.innerText = 'Select atom 1...';
                    } else {
                        measureLabel.style.display = 'none';
                    }
                    return;
                }

                // Draw spheres for selected points
                const sphereMat = new THREE.MeshBasicMaterial({ color: 0xe91e63, depthTest: false });
                const sphereGeo = new THREE.SphereGeometry(0.15, 16, 16);
                measureSelection.forEach(s => {
                    const m = new THREE.Mesh(sphereGeo, sphereMat);
                    m.position.copy(s.pos);
                    m.renderOrder = 999;
                    scene.add(m);
                    measureSpheres.push(m);
                });

                // Draw lines between selected points
                if (measureSelection.length > 1) {
                    const lineMat = new THREE.LineBasicMaterial({ color: 0xe91e63, linewidth: 2, depthTest: false });
                    const points = measureSelection.map(s => s.pos);
                    const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
                    measureLineMesh = new THREE.Line(lineGeo, lineMat);
                    measureLineMesh.renderOrder = 999;
                    scene.add(measureLineMesh);
                }

                if (measureSelection.length < 2) {
                    measureLabel.style.display = 'block';
                    measureLabel.innerText = 'Select atom 2...';
                    return;
                }

                if (measureSelection.length === 2) {
                    const d = measureSelection[0].pos.distanceTo(measureSelection[1].pos);
                    measureLabel.innerText = `Dist: ${d.toFixed(3)} Å`;
                } else if (measureSelection.length === 3) {
                    const p1 = measureSelection[0].pos;
                    const p2 = measureSelection[1].pos;
                    const p3 = measureSelection[2].pos;
                    const v1 = new THREE.Vector3().subVectors(p1, p2).normalize();
                    const v2 = new THREE.Vector3().subVectors(p3, p2).normalize();
                    const angle = v1.angleTo(v2) * 180 / Math.PI;
                    measureLabel.innerText = `Angle: ${angle.toFixed(1)}°`;
                } else if (measureSelection.length === 4) {
                    const p1 = measureSelection[0].pos;
                    const p2 = measureSelection[1].pos;
                    const p3 = measureSelection[2].pos;
                    const p4 = measureSelection[3].pos;
                    const b1 = new THREE.Vector3().subVectors(p2, p1);
                    const b2 = new THREE.Vector3().subVectors(p3, p2);
                    const b3 = new THREE.Vector3().subVectors(p4, p3);
                    const n1 = new THREE.Vector3().crossVectors(b1, b2).normalize();
                    const n2 = new THREE.Vector3().crossVectors(b2, b3).normalize();
                    const m = b2.clone().normalize();
                    const x = n1.dot(n2);
                    const y = new THREE.Vector3().crossVectors(n1, m).dot(n2);
                    const dihedral = Math.atan2(y, x) * 180 / Math.PI;
                    measureLabel.innerText = `Dihedral: ${dihedral.toFixed(1)}°`;
                }
            }

            measureBtn.addEventListener('click', () => {
                isMeasuring = !isMeasuring;
                if (isMeasuring) {
                    measureBtn.style.background = '#e91e63';
                    measureBtn.style.color = 'white';
                    updateMeasurementUI();
                } else {
                    measureBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                    measureBtn.style.color = '#333';
                    clearMeasurement();
                }
            });

            function updateInfoPanel() {
                const selectedAtoms = model.get('selected_atoms') || [];
                if (selectedAtoms.length !== 1) {
                    infoPanel.style.display = 'none';
                    return;
                }
                const idx = selectedAtoms[0];
                const cFrame = model.get('current_frame') || 0;
                const frames = model.get('data') || [];
                let positions = currentPositions || [];
                let species_list = currentSpecies || [];
                if (frames.length > 0 && frames[cFrame]) {
                    if (frames[cFrame].positions) positions = frames[cFrame].positions;
                    if (frames[cFrame].species) species_list = frames[cFrame].species;
                }

                if (idx < 0 || idx >= positions.length) {
                    infoPanel.style.display = 'none';
                    return;
                }

                const pos = positions[idx] || [0, 0, 0];
                const species = species_list[idx] !== undefined ? species_list[idx] : '?';
                const posStr = `[${pos[0].toFixed(3)}, ${pos[1].toFixed(3)}, ${pos[2].toFixed(3)}]`;

                let html = '<table style="border-collapse: collapse; text-align: left; font-family: monospace; font-size: 12px; color: #333;">';
                html += `<tr><td style="padding-right: 12px; font-weight: bold; padding-bottom: 2px;">Index:</td><td style="padding-bottom: 2px;">${idx}</td></tr>`;
                html += `<tr><td style="padding-right: 12px; font-weight: bold; padding-bottom: 2px;">Species:</td><td style="padding-bottom: 2px;">${species}</td></tr>`;
                html += `<tr><td style="padding-right: 12px; font-weight: bold;">Pos:</td><td>${posStr}</td></tr>`;
                html += '</table>';
                infoPanel.innerHTML = html;
                infoPanel.style.display = 'block';
            }

            function updateSelectionVisuals() {
                if (!atomOutlineMesh || currentNumAtoms === 0) return;

                const selectedAtoms = model.get('selected_atoms') || [];
                const drawOutlines = model.get('draw_outlines');
                const hasSelection = selectedAtoms.length > 0;

                const atomicRadiusScaler = currentStyle.atomic_radius_scaler !== undefined ? currentStyle.atomic_radius_scaler : 1.0;
                const fixedAtomicRadius = currentStyle.fixed_atomic_radius !== undefined ? currentStyle.fixed_atomic_radius : null;
                const hydrogenAtomRadius = currentStyle.hydrogen_atom_radius !== undefined ? currentStyle.hydrogen_atom_radius : null;

                for (let i = 0; i < currentNumAtoms; i++) {
                    const pos = currentPositions[i] || [0, 0, 0];
                    const sp = currentSpecies[i] !== undefined ? currentSpecies[i] : '?';
                    let rad = currentGetRadius(sp);

                    if ((sp === 1 || sp === 'H' || sp === 'h') && hydrogenAtomRadius != null) {
                        rad = hydrogenAtomRadius;
                    } else if (fixedAtomicRadius != null) {
                        rad = fixedAtomicRadius;
                    } else if (atomicRadiusScaler != null) {
                        rad = rad * atomicRadiusScaler;
                    }

                    const isSelected = selectedAtoms.includes(i);
                    dummy.position.set(pos[0], pos[1], pos[2]);
                    dummy.quaternion.identity();

                    if (drawOutlines) {
                        const outlineThickness = isSelected ? Math.max(0.04, Math.min(0.06, rad * 0.25)) : Math.min(0.04, rad * 0.2);
                        dummy.scale.set(rad + outlineThickness, rad + outlineThickness, rad + outlineThickness);
                        dummy.updateMatrix();
                        atomOutlineMesh.setMatrixAt(i, dummy.matrix);
                        atomOutlineMesh.setColorAt(i, isSelected ? selectedOutlineColor : defaultOutlineColor);
                    } else {
                        if (isSelected) {
                            const outlineThickness = Math.max(0.04, Math.min(0.06, rad * 0.25));
                            dummy.scale.set(rad + outlineThickness, rad + outlineThickness, rad + outlineThickness);
                            dummy.updateMatrix();
                            atomOutlineMesh.setMatrixAt(i, dummy.matrix);
                            atomOutlineMesh.setColorAt(i, selectedOutlineColor);
                        } else {
                            dummy.scale.set(0, 0, 0);
                            dummy.updateMatrix();
                            atomOutlineMesh.setMatrixAt(i, dummy.matrix);
                            atomOutlineMesh.setColorAt(i, defaultOutlineColor);
                        }
                    }
                }

                atomOutlineMesh.instanceMatrix.needsUpdate = true;
                if (atomOutlineMesh.instanceColor) atomOutlineMesh.instanceColor.needsUpdate = true;

                if (drawOutlines || hasSelection) {
                    if (atomOutlineMesh.parent !== scene) {
                        scene.add(atomOutlineMesh);
                    }
                } else {
                    if (atomOutlineMesh.parent === scene) {
                        scene.remove(atomOutlineMesh);
                    }
                }
            }

            model.on("change:selected_atoms", () => {
                updateSelectionVisuals();
                updateInfoPanel();
            });
            model.on("change:current_frame", () => {
                const selected = model.get('selected_atoms') || [];
                if (selected.length > 0) {
                    model.set('selected_atoms', []);
                    model.save_changes();
                }
                updateSelectionVisuals();
                updateInfoPanel();
            });

            function togglePlay() {
                isPlaying = !isPlaying;
                btnPlay.innerHTML = isPlaying ? iconPause : iconPlay;
                if (isPlaying) {
                    const fps = model.get('traj_fps') || 10;
                    const intervalMs = Math.max(1, Math.round(1000 / fps));
                    animationInterval = setInterval(() => {
                        const frames = model.get('data') || [];
                        if (frames.length === 0) return;
                        let next = model.get('current_frame') + 1;
                        if (next >= frames.length) next = 0; // loop
                        setFrame(next);
                    }, intervalMs);
                } else {
                    if (animationInterval) clearInterval(animationInterval);
                }
            }

            function setFrame(idx) {
                const frames = model.get('data') || [];
                if (!frames || frames.length === 0) return;
                if (idx < 0) idx = frames.length - 1;
                if (idx >= frames.length) idx = 0;
                model.set('current_frame', idx);
                model.set('selected_atoms', []);
                model.save_changes();
                frameSlider.value = String(idx);
                updateScene();
            }

            let isCameraInitialized = false;

            function updateScene(forceFitCamera = false) {
                const frames = model.get('data') || [];
                const isTrajectory = frames.length > 1;

                let positions = [], species = [], bonds = [], unitCell = [], customLabels = [], customHighlight = [], extraData = null;
                if (isTrajectory) {
                    uiContainer.style.display = 'flex';
                    btnPlay.style.display = model.get('multi_traj') !== false ? 'flex' : 'none';
                    const cFrame = model.get('current_frame');
                    frameCounter.innerText = `${cFrame + 1} / ${frames.length}`;
                    frameSlider.max = String(Math.max(0, frames.length - 1));
                    frameSlider.value = String(cFrame);
                    frameSlider.style.display = model.get('trajectory_slider') ? 'block' : 'none';

                    const fData = frames[cFrame] || {};
                    positions = fData.positions || [];
                    species = fData.species || [];
                    bonds = fData.bonds || [];
                    unitCell = fData.unit_cell || [];
                    customLabels = fData.labels || [];
                    customHighlight = fData.highlight || [];
                    extraData = fData.extra_data || null;
                } else {
                    uiContainer.style.display = 'none';
                    const fData = frames[0] || {};
                    positions = fData.positions || [];
                    species = fData.species || [];
                    bonds = fData.bonds || [];
                    unitCell = fData.unit_cell || [];
                    customLabels = fData.labels || [];
                    customHighlight = fData.highlight || [];
                    extraData = fData.extra_data || null;
                }

                if (extraData && Object.keys(extraData).length > 0) {
                    extraDataContainer.style.display = 'flex';
                    let html = '<table style="border-collapse: collapse; text-align: left;">';
                    const entries = Object.entries(extraData);
                    for (let i = 0; i < entries.length; i++) {
                        const [k, v] = entries[i];
                        let valStr = v;
                        if (typeof v === 'number' && !Number.isInteger(v)) {
                            valStr = v.toFixed(4);
                        } else if (typeof v === 'object') {
                            valStr = JSON.stringify(v);
                        }
                        const borderStyle = (i === entries.length - 1) ? '' : 'border-bottom: 1px solid rgba(0,0,0,0.1); ';
                        html += `<tr><td style="padding-right: 12px; font-weight: bold; ${borderStyle}padding-top: 4px; padding-bottom: 4px;">${k}</td><td style="${borderStyle}padding-top: 4px; padding-bottom: 4px;">${valStr}</td></tr>`;
                    }
                    html += '</table>';
                    extraDataPanel.innerHTML = html;
                } else {
                    extraDataContainer.style.display = 'none';
                    if (isExtraDataOpen) extraDataBtn.click();
                }

                const style = model.get('style') || {};
                const bondRadius = style.bond_radius !== undefined ? style.bond_radius : 0.0;
                const atomicRadiusScaler = style.atomic_radius_scaler !== undefined ? style.atomic_radius_scaler : 1.0;
                const fixedAtomicRadius = style.fixed_atomic_radius !== undefined ? style.fixed_atomic_radius : null;
                const hydrogenAtomRadius = style.hydrogen_atom_radius !== undefined ? style.hydrogen_atom_radius : null;
                const isWireframe = (bondRadius === 0.05 && fixedAtomicRadius === 0.05);
                const numAtoms = positions.length;

                const colorMap = model.get('color_map') || {};
                const radiusMap = model.get('radius_map') || {};
                const defaultColor = model.get('default_color') || [1, 0.08, 0.58];
                const defaultRadius = model.get('default_radius') || 0.8;

                const capitalize = (s) => (typeof s === 'string' && s.length > 0) ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : String(s);
                const getColor = (sp) => {
                    const c = colorMap[capitalize(sp)];
                    return c !== undefined ? c : defaultColor;
                };
                const getRadius = (sp) => {
                    const r = radiusMap[capitalize(sp)];
                    return r !== undefined ? r : defaultRadius;
                };

                // Clear old meshes
                if (atomMesh) { scene.remove(atomMesh); atomMesh.dispose(); atomMesh = null; }
                if (bondMesh) { scene.remove(bondMesh); bondMesh.dispose(); bondMesh = null; }
                if (atomOutlineMesh) { scene.remove(atomOutlineMesh); atomOutlineMesh.dispose(); atomOutlineMesh = null; }
                if (bondOutlineMesh) { scene.remove(bondOutlineMesh); bondOutlineMesh.dispose(); bondOutlineMesh = null; }
                clearMeasurement();
                if (isMeasuring) {
                    measureLabel.style.display = 'block';
                    measureLabel.innerText = 'Select atom 1...';
                }
                if (cellGroup) {
                    scene.remove(cellGroup);
                    cellGroup.traverse((child) => {
                        if (child.geometry) child.geometry.dispose();
                        if (child.material) {
                            if (child.material.map) child.material.map.dispose();
                            child.material.dispose();
                        }
                    });
                    cellGroup = null;
                }

                // Determine styling parameters
                let showBonds = bondRadius > 0 && bonds.length > 0;
                const drawOutlines = model.get('draw_outlines');

                // --- ATOM LABELS ---
                labelsContainer.innerHTML = '';
                labelElements = [];
                const drawLabels = model.get('draw_labels');
                if (drawLabels) {
                    for (let i = 0; i < numAtoms; i++) {
                        let txt = species[i] !== undefined ? species[i] : '?';
                        if (customLabels[i] !== undefined && customLabels[i] !== null) {
                            txt = customLabels[i];
                        }
                        const el = document.createElement('div');
                        el.innerText = txt;
                        el.style.position = 'absolute';
                        el.style.color = '#000';
                        el.style.fontWeight = 'bold';
                        el.style.fontSize = '12px';
                        el.style.fontFamily = 'sans-serif';
                        el.style.textShadow = '1px 1px 0 #fff, -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff';
                        el.style.pointerEvents = 'none';
                        el.style.left = '0px';
                        el.style.top = '0px';
                        el.style.transform = 'translate(-50%, -50%)';
                        labelsContainer.appendChild(el);

                        labelElements.push({
                            el: el,
                            pos: new THREE.Vector3().fromArray(positions[i] || [0,0,0]),
                            index: i
                        });
                    }
                }

                // Store current state for dynamic selection updates
                currentPositions = positions;
                currentSpecies = species;
                currentNumAtoms = numAtoms;
                currentStyle = style;
                currentGetRadius = getRadius;

                // --- ATOMS ---
                atomMesh = new THREE.InstancedMesh(sphereGeometry, sphereMaterial, numAtoms);
                atomOutlineMesh = new THREE.InstancedMesh(sphereGeometry, outlineMaterial, numAtoms);
                atomOutlineMesh.renderOrder = 1;
                let centerSum = new THREE.Vector3(0, 0, 0);

                for (let i = 0; i < numAtoms; i++) {
                    const pos = positions[i] || [0, 0, 0];
                    const sp = species[i] !== undefined ? species[i] : '?';
                    const col = getColor(sp);
                    let rad = getRadius(sp);

                    if ((sp === 1 || sp === 'H' || sp === 'h') && hydrogenAtomRadius != null) {
                        rad = hydrogenAtomRadius;
                    } else if (fixedAtomicRadius != null) {
                        rad = fixedAtomicRadius;
                    } else if (atomicRadiusScaler != null) {
                        rad = rad * atomicRadiusScaler;
                    }

                    dummy.position.set(pos[0], pos[1], pos[2]);
                    dummy.scale.set(rad, rad, rad);
                    // Reset rotation just in case
                    dummy.quaternion.identity();
                    dummy.updateMatrix();
                    atomMesh.setMatrixAt(i, dummy.matrix);

                    if (customHighlight && customHighlight.includes(i)) {
                        colorObj.setRGB(0, 1, 1);
                    } else {
                        colorObj.setRGB(col[0], col[1], col[2]);
                    }
                    atomMesh.setColorAt(i, colorObj);

                    centerSum.add(dummy.position);
                }

                atomMesh.instanceMatrix.needsUpdate = true;
                if (atomMesh.instanceColor) atomMesh.instanceColor.needsUpdate = true;
                scene.add(atomMesh);

                updateSelectionVisuals();
                updateInfoPanel();

                // --- BONDS ---
                if (showBonds && bonds.length > 0) {
                    bondMesh = new THREE.InstancedMesh(cylinderGeometry, cylinderMaterial, bonds.length * 2);
                    if (drawOutlines) {
                        bondOutlineMesh = new THREE.InstancedMesh(cylinderGeometry, bondOutlineMaterial, bonds.length);
                        bondOutlineMesh.renderOrder = 1;
                    }


                    const vA = new THREE.Vector3();
                    const vB = new THREE.Vector3();
                    const vDir = new THREE.Vector3();
                    const vMid = new THREE.Vector3();

                    for (let i = 0; i < bonds.length; i++) {
                        const b = bonds[i];

                        vA.fromArray(positions[b.source] || [0,0,0]);
                        vB.fromArray(positions[b.target] || [0,0,0]);
                        vMid.copy(vA).lerp(vB, 0.5);

                        const distance = vA.distanceTo(vMid);
                        vDir.subVectors(vB, vA).normalize();

                        // First half (Atom A to Midpoint)
                        dummy.position.copy(vA).lerp(vMid, 0.5);
                        dummy.scale.set(bondRadius, distance, bondRadius);
                        dummy.quaternion.setFromUnitVectors(yAxis, vDir);
                        dummy.updateMatrix();
                        bondMesh.setMatrixAt(i * 2, dummy.matrix);

                        if (customHighlight && customHighlight.includes(b.source)) {
                            colorObj.setRGB(0, 1, 1);
                        } else {
                            const colA = getColor(species[b.source]);
                            colorObj.setRGB(colA[0], colA[1], colA[2]);
                        }
                        bondMesh.setColorAt(i * 2, colorObj);

                        // Second half (Midpoint to Atom B)
                        dummy.position.copy(vMid).lerp(vB, 0.5);
                        dummy.scale.set(bondRadius, distance, bondRadius);
                        // quaternion stays the same since direction is the same
                        dummy.updateMatrix();
                        bondMesh.setMatrixAt(i * 2 + 1, dummy.matrix);

                        if (customHighlight && customHighlight.includes(b.target)) {
                            colorObj.setRGB(0, 1, 1);
                        } else {
                            const colB = getColor(species[b.target]);
                            colorObj.setRGB(colB[0], colB[1], colB[2]);
                        }
                        bondMesh.setColorAt(i * 2 + 1, colorObj);

                        // Single full-length outline cylinder
                        if (drawOutlines) {
                            const fullDist = vA.distanceTo(vB);
                            const outlineThickness = Math.min(0.04, bondRadius * 0.2);
                            dummy.position.copy(vMid);
                            dummy.scale.set(bondRadius + outlineThickness, fullDist, bondRadius + outlineThickness);
                            // quaternion is already set correctly for the direction
                            dummy.updateMatrix();
                            bondOutlineMesh.setMatrixAt(i, dummy.matrix);
                        }
                    }
                    bondMesh.instanceMatrix.needsUpdate = true;
                    if (bondMesh.instanceColor) bondMesh.instanceColor.needsUpdate = true;
                    scene.add(bondMesh);
                    if (drawOutlines) {
                        bondOutlineMesh.instanceMatrix.needsUpdate = true;
                        scene.add(bondOutlineMesh);
                    }
                }

                // --- UNIT CELL ---
                let cellCenter = null;
                if (unitCell && unitCell.length === 3) {
                    const v1 = new THREE.Vector3().fromArray(unitCell[0]);
                    const v2 = new THREE.Vector3().fromArray(unitCell[1]);
                    const v3 = new THREE.Vector3().fromArray(unitCell[2]);

                    const origin = new THREE.Vector3(0,0,0);
                    const p12 = v1.clone().add(v2);
                    const p13 = v1.clone().add(v3);
                    const p23 = v2.clone().add(v3);
                    const p123 = v1.clone().add(v2).add(v3);

                    cellGroup = new THREE.Group();

                    // Helper to create thick cylinders for main vectors
                    const createThickVector = (v, colorHex) => {
                        const len = v.length();
                        const mat = new THREE.MeshPhongMaterial({ color: colorHex, shininess: 60 });
                        const geo = new THREE.CylinderGeometry(0.04, 0.04, len, 8);
                        geo.translate(0, len / 2, 0);
                        const mesh = new THREE.Mesh(geo, mat);

                        const q = new THREE.Quaternion();
                        q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v.clone().normalize());
                        mesh.setRotationFromQuaternion(q);
                        return mesh;
                    };

                    // a, b, c vectors as thick shaded cylinders
                    cellGroup.add(createThickVector(v1, 0xff4444));
                    cellGroup.add(createThickVector(v2, 0x44ff44));
                    cellGroup.add(createThickVector(v3, 0x4444ff));

                    const vertices = [];
                    const addEdge = (p1, p2) => {
                        vertices.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
                    };

                    // Remaining unit cell edges as thin wireframes
                    addEdge(v1, p12); addEdge(v1, p13);
                    addEdge(v2, p12); addEdge(v2, p23);
                    addEdge(v3, p13); addEdge(v3, p23);
                    addEdge(p12, p123); addEdge(p13, p123); addEdge(p23, p123);

                    const geo = new THREE.BufferGeometry();
                    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
                    const mat = new THREE.LineBasicMaterial({ color: 0x888888 });
                    const cellLines = new THREE.LineSegments(geo, mat);
                    cellGroup.add(cellLines);

                    const aLbl = createLabel('a', '#ff4444', v1.clone().add(v1.clone().normalize().multiplyScalar(0.2)));
                    aLbl.scale.set(0.4, 0.4, 0.4); cellGroup.add(aLbl);

                    const bLbl = createLabel('b', '#44ff44', v2.clone().add(v2.clone().normalize().multiplyScalar(0.2)));
                    bLbl.scale.set(0.4, 0.4, 0.4); cellGroup.add(bLbl);

                    const cLbl = createLabel('c', '#4444ff', v3.clone().add(v3.clone().normalize().multiplyScalar(0.2)));
                    cLbl.scale.set(0.4, 0.4, 0.4); cellGroup.add(cLbl);

                    scene.add(cellGroup);

                    cellCenter = p123.clone().multiplyScalar(0.5);
                }

                if (numAtoms === 0 && !cellGroup) return;

                // Auto-center and fit camera
                const sceneCenter = new THREE.Vector3();
                if (cellCenter) {
                    sceneCenter.copy(cellCenter);
                } else if (numAtoms > 0) {
                    centerSum.divideScalar(numAtoms);
                    sceneCenter.copy(centerSum);
                }

                if (!isCameraInitialized || forceFitCamera === true) {
                    controls.target.copy(sceneCenter);

                    let maxDist = 0;
                    if (cellCenter) {
                        // Base maxDist on the distance from cell center to the origin (half the main diagonal)
                        maxDist = cellCenter.length();
                    } else if (numAtoms > 0) {
                        for (let i = 0; i < numAtoms; i++) {
                            const pos = new THREE.Vector3().fromArray(positions[i] || [0,0,0]);
                            const dist = pos.distanceTo(sceneCenter);
                            if (dist > maxDist) maxDist = dist;
                        }
                    }

                    const cameraDist = Math.max(10, maxDist * 3);

                    if (camera.isOrthographicCamera) {
                        const aspect = container.clientWidth / container.clientHeight;
                        // Provide a 1.5x margin so the molecule fits comfortably
                        camera.left = -maxDist * aspect * 1.5;
                        camera.right = maxDist * aspect * 1.5;
                        camera.top = maxDist * 1.5;
                        camera.bottom = -maxDist * 1.5;
                        camera.updateProjectionMatrix();
                    }

                    camera.position.set(sceneCenter.x, sceneCenter.y, sceneCenter.z + cameraDist);

                    controls.update();
                    isCameraInitialized = true;

                    if (model.get('fog') && model.get('fog_strength') > 0) {
                        const bgColor = model.get('background_color') || '#ffffff';
                        const strength = model.get('fog_strength') || 0.5;
                        const invS = 1.0 / strength;
                        // Fog starts near the center of the molecule and fully obscures past the back, scaled by strength
                        scene.fog = new THREE.Fog(bgColor, cameraDist - maxDist * 0.5 * invS, cameraDist + maxDist * 1.5 * invS);
                    } else {
                        scene.fog = null;
                    }
                } else {
                    const targetDelta = new THREE.Vector3().subVectors(sceneCenter, controls.target);
                    if (targetDelta.lengthSq() > 0.0001) {
                        controls.target.copy(sceneCenter);
                        camera.position.add(targetDelta);
                        controls.update();
                    }
                }

                if (isHelpOpen) {
                    updateHelpContent();
                }
            }

            // Watch for changes from Python
            model.on("change:data", () => updateScene(true));
            model.on("change:style", () => updateScene(false));
            model.on("change:width", () => {
                container.style.width = model.get('width') || '100%';
            });
            model.on("change:height", () => {
                container.style.height = model.get('height') || '400px';
            });
            model.on("change:viewer_outline", applyOutline);
            model.on("change:fog", () => updateScene(true));
            model.on("change:fog_strength", () => updateScene(true));
            model.on("change:draw_outlines", () => updateScene(true));
            model.on("change:draw_labels", () => updateScene(true));
            model.on("change:show_axes", () => {
                if (isHelpOpen) updateHelpContent();
            });
            model.on("change:show_help", () => {
                const show = model.get('show_help');
                helpContainer.style.display = show ? 'flex' : 'none';
                if (!show && isHelpOpen) {
                    toggleHelp(false);
                }
            });
            model.on("change:recording_tools", () => {
                const show = model.get('recording_tools');
                captureContainer.style.display = show ? 'flex' : 'none';
                if (!show && isRecording) {
                    stopRecording();
                }
                if (isHelpOpen) updateHelpContent();
            });
            model.on("change:multi_traj", () => {
                const showPlay = model.get('multi_traj') !== false;
                btnPlay.style.display = showPlay ? 'flex' : 'none';
                if (!showPlay && isPlaying) {
                    togglePlay();
                }
            });
            model.on("change:trajectory_slider", () => {
                const frames = model.get('data') || [];
                const isTrajectory = frames.length > 1;
                frameSlider.style.display = (model.get('trajectory_slider') && isTrajectory) ? 'block' : 'none';
                if (isHelpOpen) updateHelpContent();
            });
            model.on("change:traj_fps", () => {
                if (isPlaying) {
                    if (animationInterval) clearInterval(animationInterval);
                    const fps = model.get('traj_fps') || 10;
                    const intervalMs = Math.max(1, Math.round(1000 / fps));
                    animationInterval = setInterval(() => {
                        const frames = model.get('data') || [];
                        if (frames.length === 0) return;
                        let next = model.get('current_frame') + 1;
                        if (next >= frames.length) next = 0;
                        setFrame(next);
                    }, intervalMs);
                }
            });
            model.on("change:background_color", () => {
                container.style.backgroundColor = model.get('background_color');
                if (scene.fog) {
                    scene.fog.color.set(model.get('background_color'));
                }
            });
            model.on("change:projection", () => {
                const newProj = model.get('projection');
                const newCamera = newProj === 'orthographic' ? orthoCamera : persCamera;
                if (camera !== newCamera) {
                    newCamera.position.copy(camera.position);
                    newCamera.quaternion.copy(camera.quaternion);

                    camera = newCamera;
                    controls.object = camera;

                    if (panX !== 0 || panY !== 0) {
                        camera.setViewOffset(container.clientWidth, container.clientHeight, panX, panY, container.clientWidth, container.clientHeight);
                    } else {
                        camera.clearViewOffset();
                    }
                    updateScene(true);
                }
            });
            updateScene();

            // Custom Panning using viewOffset
            let panX = 0;
            let panY = 0;
            let isPanning = false;

            container.addEventListener('contextmenu', e => e.preventDefault());

            container.addEventListener('mousedown', (e) => {
                if (e.button === 2) {
                    isPanning = true;
                }
            });
            container.addEventListener('mousemove', (e) => {
                if (isPanning) {
                    panX -= e.movementX;
                    panY -= e.movementY;
                    camera.setViewOffset(
                        container.clientWidth, container.clientHeight,
                        panX, panY,
                        container.clientWidth, container.clientHeight
                    );
                    camera.updateProjectionMatrix();
                }
            });
            container.addEventListener('mouseup', (e) => {
                if (e.button === 2) isPanning = false;
            });
            container.addEventListener('mouseleave', () => {
                isPanning = false;
            });

            // Handle Resize
            const resizeObserver = new ResizeObserver(() => {
                if (container.clientWidth === 0 || container.clientHeight === 0) return;
                const aspect = container.clientWidth / container.clientHeight;

                if (camera.isOrthographicCamera) {
                    const height = camera.top;
                    camera.left = -height * aspect;
                    camera.right = height * aspect;
                } else {
                    camera.aspect = aspect;
                }

                if (panX !== 0 || panY !== 0) {
                    camera.setViewOffset(container.clientWidth, container.clientHeight, panX, panY, container.clientWidth, container.clientHeight);
                } else {
                    camera.clearViewOffset();
                }
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
                controls.handleResize();
            });
            resizeObserver.observe(container);

            // Handle KeyDown for Help Overlay and Shortcuts Toggle
            let isContainerHovered = false;
            container.addEventListener('mouseenter', () => { isContainerHovered = true; });
            container.addEventListener('mouseleave', () => { isContainerHovered = false; });

            const handleKeyDown = (e) => {
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;

                const isTargetInside = container.contains(e.target) || isContainerHovered || document.activeElement === container;
                if (!isTargetInside) return;

                if (model.get('show_help')) {
                    if ((e.key === 'h' || e.key === 'H') && !e.ctrlKey && !e.metaKey && !e.altKey) {
                        e.preventDefault();
                        toggleHelp();
                        return;
                    } else if (e.key === 'Escape' && isHelpOpen) {
                        e.preventDefault();
                        toggleHelp(false);
                        return;
                    }
                }

                if (model.get('recording_tools')) {
                    if ((e.key === 's' || e.key === 'S') && !e.ctrlKey && !e.metaKey && !e.altKey) {
                        e.preventDefault();
                        captureScreenshot();
                    } else if ((e.key === 'r' || e.key === 'R') && !e.ctrlKey && !e.metaKey && !e.altKey) {
                        e.preventDefault();
                        toggleRecording();
                    }
                }
            };

            window.addEventListener('keydown', handleKeyDown);

            // Handle Click (Picking or Axis Snapping)
            let pointerDownPos = { x: 0, y: 0 };
            container.addEventListener('pointerdown', (e) => {
                pointerDownPos = { x: e.clientX, y: e.clientY };
            });

            container.addEventListener('click', (event) => {
                if (isHelpOpen) {
                    toggleHelp(false);
                    return;
                }

                const dx = event.clientX - pointerDownPos.x;
                const dy = event.clientY - pointerDownPos.y;
                if (Math.sqrt(dx * dx + dy * dy) > 5) return;

                const rect = container.getBoundingClientRect();
                const cx = event.clientX - rect.left;
                const cy = event.clientY - rect.top;

                // 1. Check if click is inside the axes overlay (bottom left, 10 to 90)
                if (model.get('show_axes') && cx >= 10 && cx <= 90 && cy >= container.clientHeight - 90 && cy <= container.clientHeight - 10) {
                    const axX = ((cx - 10) / 80) * 2 - 1;
                    const axY = -((cy - (container.clientHeight - 90)) / 80) * 2 + 1;

                    const axesMouse = new THREE.Vector2(axX, axY);
                    raycaster.setFromCamera(axesMouse, axesCamera);
                    const intersects = raycaster.intersectObjects(axesScene.children, true);

                    if (intersects.length > 0) {
                        for (const hit of intersects) {
                            if (hit.object.name === 'X' || hit.object.name === 'Y' || hit.object.name === 'Z') {
                                const dist = camera.position.distanceTo(controls.target);
                                if (hit.object.name === 'X') {
                                    camera.position.copy(controls.target).add(new THREE.Vector3(dist, 0, 0));
                                    camera.up.set(0, 1, 0);
                                } else if (hit.object.name === 'Y') {
                                    camera.position.copy(controls.target).add(new THREE.Vector3(0, dist, 0));
                                    camera.up.set(0, 0, -1);
                                } else if (hit.object.name === 'Z') {
                                    camera.position.copy(controls.target).add(new THREE.Vector3(0, 0, dist));
                                    camera.up.set(0, 1, 0);
                                }
                                camera.lookAt(controls.target);
                                controls.update();
                                return; // Stop processing, we handled the axes click
                            }
                        }
                    }
                }

                // 2. Otherwise process atom picking in the main scene
                mouse.x = (cx / container.clientWidth) * 2 - 1;
                mouse.y = -(cy / container.clientHeight) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);

                if (atomMesh) {
                    const intersects = raycaster.intersectObject(atomMesh);
                    if (intersects.length > 0) {
                        // The instanceId tells us which atom was clicked
                        const instanceId = intersects[0].instanceId;
                        if (isMeasuring) {
                            if (measureSelection.length >= 4) {
                                measureSelection = [];
                            }
                            const dummyMat = new THREE.Matrix4();
                            atomMesh.getMatrixAt(instanceId, dummyMat);
                            const pos = new THREE.Vector3();
                            pos.setFromMatrixPosition(dummyMat);
                            measureSelection.push({ index: instanceId, pos: pos });
                            updateMeasurementUI();
                        } else {
                            let currentSelected = [...(model.get('selected_atoms') || [])];
                            if (event.shiftKey) {
                                if (currentSelected.includes(instanceId)) {
                                    currentSelected = currentSelected.filter(id => id !== instanceId);
                                } else {
                                    currentSelected.push(instanceId);
                                }
                            } else {
                                currentSelected = [instanceId];
                            }
                            model.set("selected_atoms", currentSelected);
                            model.save_changes();
                            updateSelectionVisuals();
                            updateInfoPanel();
                        }
                    } else {
                        if (isMeasuring) {
                            measureSelection = [];
                            updateMeasurementUI();
                        } else {
                            if (!event.shiftKey) {
                                model.set("selected_atoms", []);
                                model.save_changes();
                                updateSelectionVisuals();
                                updateInfoPanel();
                            }
                        }
                    }
                }
            });

            // Render Loop
            let animationId;
            const _vec = new THREE.Vector3();
            const _labelRaycaster = new THREE.Raycaster();
            function animate() {
                animationId = requestAnimationFrame(animate);

                if (model.get("spin") && model.get("spin_speed") !== 0) {
                    const speed = model.get("spin_speed") * 0.01;
                    const axisArr = model.get("spin_axis");
                    const axis = new THREE.Vector3(axisArr[0], axisArr[1], axisArr[2]).normalize();
                    if (axis.lengthSq() > 0.001) {
                        camera.position.sub(controls.target);
                        camera.position.applyAxisAngle(axis, speed);
                        camera.position.add(controls.target);

                        camera.up.applyAxisAngle(axis, speed);
                        camera.lookAt(controls.target);
                    }
                }

                controls.update();

                // Update Labels
                if (labelElements.length > 0) {
                    const hw = container.clientWidth / 2;
                    const hh = container.clientHeight / 2;
                    camera.updateMatrixWorld();
                    for (let i = 0; i < labelElements.length; i++) {
                        const item = labelElements[i];
                        _vec.copy(item.pos).project(camera);
                        if (_vec.z > 1.0 || _vec.z < -1.0) {
                            item.el.style.display = 'none';
                        } else {
                            // Occlusion test
                            _labelRaycaster.setFromCamera(_vec, camera);
                            let occluded = false;
                            if (atomMesh) {
                                const hits = _labelRaycaster.intersectObject(atomMesh);
                                if (hits.length > 0 && hits[0].instanceId !== item.index) {
                                    occluded = true;
                                } else if (bondMesh) {
                                    const bHits = _labelRaycaster.intersectObject(bondMesh);
                                    if (bHits.length > 0 && hits.length > 0 && bHits[0].distance < hits[0].distance) {
                                        occluded = true;
                                    }
                                }
                            }

                            if (occluded) {
                                item.el.style.display = 'none';
                            } else {
                                item.el.style.display = 'block';
                                const x = (_vec.x * hw) + hw;
                                const y = -(_vec.y * hh) + hh;
                                item.el.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px)`;
                            }
                        }
                    }
                }

                // 1. Render main scene
                renderer.setViewport(0, 0, container.clientWidth, container.clientHeight);
                renderer.clear();
                renderer.render(scene, camera);

                // 2. Render axes overlay in bottom left if requested
                if (model.get('show_axes')) {
                    // Position axes camera behind the origin to match main camera orientation
                    axesCamera.position.copy(camera.position).sub(controls.target).normalize().multiplyScalar(4);
                    // Instead of lookAt (which suffers from Gimbal lock when aligned with Y), directly copy the exact rotation
                    axesCamera.quaternion.copy(camera.quaternion);

                    renderer.clearDepth();
                    // Draw in bottom left corner (80x80)
                    renderer.setViewport(10, 10, 80, 80);
                    renderer.render(axesScene, axesCamera);
                }

                // 3. Composite recording frame if recording with custom background or UI
                if (isRecording && recordCanvas && recordCtx) {
                    const rW = recordCanvas.width;
                    const rH = recordCanvas.height;
                    const includeBgd = model.get('record_include_bgd');
                    const includeUi = model.get('record_include_ui');
                    if (includeBgd) {
                        recordCtx.fillStyle = model.get('background_color') || '#ffffff';
                        recordCtx.fillRect(0, 0, rW, rH);
                    } else {
                        recordCtx.clearRect(0, 0, rW, rH);
                    }
                    recordCtx.drawImage(renderer.domElement, 0, 0, rW, rH);
                    if (includeUi) {
                        const targetPixelRatio = renderer.getPixelRatio() || 1;
                        drawOverlaysToCanvas(recordCtx, targetPixelRatio);
                    }
                }
            }
            animate();

            // Cleanup when cell is deleted or widget is destroyed
            return () => {
                cancelAnimationFrame(animationId);
                resizeObserver.disconnect();
                window.removeEventListener('keydown', handleKeyDown);
                if (isRecording) {
                    stopRecording();
                }
                if (recordTimerInterval) {
                    clearInterval(recordTimerInterval);
                }
                recordCanvas = null;
                recordCtx = null;
                if (atomMesh) {
                    atomMesh.dispose();
                    scene.remove(atomMesh);
                }
                if (atomOutlineMesh) {
                    atomOutlineMesh.dispose();
                    scene.remove(atomOutlineMesh);
                }
                if (bondMesh) {
                    bondMesh.dispose();
                    scene.remove(bondMesh);
                }
                if (bondOutlineMesh) {
                    bondOutlineMesh.dispose();
                    scene.remove(bondOutlineMesh);
                }
                renderer.dispose();
            };
        }
    }
    """
    data = traitlets.List(default_value=[]).tag(sync=True)
    color_map = traitlets.Dict().tag(sync=True)
    radius_map = traitlets.Dict().tag(sync=True)
    default_color = traitlets.List().tag(sync=True)
    default_radius = traitlets.Float().tag(sync=True)

    current_frame = traitlets.Int(0).tag(sync=True)
    selected_atoms = traitlets.List(default_value=[]).tag(sync=True)
    background_color = traitlets.Unicode("#ffffff").tag(sync=True)
    style = traitlets.Dict().tag(sync=True)
    show_axes = traitlets.Bool(False).tag(sync=True)
    projection = traitlets.Unicode("orthographic").tag(sync=True)  # 'perspective' or 'orthographic'
    width = traitlets.Unicode("100%").tag(sync=True)
    height = traitlets.Unicode("400px").tag(sync=True)
    viewer_outline = traitlets.Any(default_value=False).tag(sync=True)  # bool or str
    fog = traitlets.Bool(False).tag(sync=True)
    fog_strength = traitlets.Float(0.5).tag(sync=True)
    draw_outlines = traitlets.Bool(False).tag(sync=True)
    draw_labels = traitlets.Bool(False).tag(sync=True)
    measuring_tool = traitlets.Bool(False).tag(sync=True)
    spin = traitlets.Bool(False).tag(sync=True)
    spin_axis = traitlets.List(default_value=[0.0, 1.0, 0.0]).tag(sync=True)
    spin_speed = traitlets.Float(2.0).tag(sync=True)
    multi_traj = traitlets.Bool(True).tag(sync=True)
    traj_fps = traitlets.Float(10.0).tag(sync=True)
    trajectory_slider = traitlets.Bool(False).tag(sync=True)
    show_help = traitlets.Bool(True).tag(sync=True)
    recording_tools = traitlets.Bool(False).tag(sync=True)
    dpi = traitlets.Int(200).tag(sync=True)
    record_include_bgd = traitlets.Bool(False).tag(sync=True)
    record_include_ui = traitlets.Bool(False).tag(sync=True)


STYLES = {
    "vdw": {
        "bond_radius": 0.0,
        "atomic_radius_scaler": 1.0,
        "hydrogen_atom_radius": None,
        "fixed_atomic_radius": None,
        "use_vdw_radii": True,
    },
    "ball-and-stick": {
        "bond_radius": 0.15,
        "atomic_radius_scaler": None,
        "hydrogen_atom_radius": 0.25,
        "fixed_atomic_radius": 0.45,
        "use_vdw_radii": False,
    },
    "wireframe": {
        "bond_radius": 0.05,
        "atomic_radius_scaler": None,
        "hydrogen_atom_radius": 0.05,
        "fixed_atomic_radius": 0.05,
        "use_vdw_radii": False,
    },
}


_UNSET = object()

DEFAULT_VIEWER_CONFIG = {
    "style": "ball-and-stick",
    "background_color": "white",
    "show_axes": False,
    "projection": "orthographic",
    "width": "100%",
    "height": "400px",
    "viewer_outline": False,
    "fog": False,
    "fog_strength": 0.5,
    "draw_outlines": False,
    "draw_labels": False,
    "measuring_tool": False,
    "unwrap_molecules": False,
    "spin": False,
    "spin_axis": (0.0, 1.0, 0.0),
    "spin_speed": 2.0,
    "multi_traj": True,
    "traj_fps": 10.0,
    "trajectory_slider": False,
    "compute_extra_data": False,
    "show_help": True,
    "recording_tools": False,
    "dpi": 200,
    "record_include_bgd": False,
    "record_include_ui": False,
}


def view_structure(
    data: dict | list[dict],
    config: dict | str | os.PathLike | None = None,
    style: str | dict = _UNSET,
    background_color: str = _UNSET,
    show_axes: bool = _UNSET,
    projection: str = _UNSET,
    width: str = _UNSET,
    height: str = _UNSET,
    viewer_outline: bool | str = _UNSET,
    fog: bool = _UNSET,
    fog_strength: float = _UNSET,
    draw_outlines: bool = _UNSET,
    draw_labels: bool = _UNSET,
    measuring_tool: bool = _UNSET,
    unwrap_molecules: bool = _UNSET,
    spin: bool = _UNSET,
    spin_axis: tuple[float, float, float] | list[float] = _UNSET,
    spin_speed: float = _UNSET,
    multi_traj: bool = _UNSET,
    traj_fps: float = _UNSET,
    trajectory_slider: bool = _UNSET,
    compute_extra_data: bool = _UNSET,
    show_help: bool = _UNSET,
    recording_tools: bool = _UNSET,
    dpi: int = _UNSET,
    record_include_bgd: bool = _UNSET,
    record_include_ui: bool = _UNSET,
) -> mo.ui.anywidget:
    """
    Visualize a molecule or periodic structure in the notebook.

    Parameters
    ----------
    data : dict or list[dict]
        A dictionary with keys 'positions', 'species', 'bonds' (optional), 'unit_cell' (optional),
        'labels' (optional), 'highlight' (optional), 'extra_data' (optional) or a list of such dictionaries
        for a trajectory.
    config : dict, str, or os.PathLike, optional
        A dictionary, path to a TOML file (PathLike or str), or a TOML formatted string containing configuration
        settings. Default is None. Any explicitly provided arguments to view_structure will override the settings in config.
        *(added in v0.2.0)*
    style : str or dict, optional
        Style options: 'ball-and-stick' (default), 'vdw', 'wireframe' or a custom dictionary.
    background_color : str, optional
        Background color of the viewer. Default is "white".
    show_axes : bool, optional
        Whether to display XYZ axes in the corner. Default is False.
    projection : str, optional
        Projection type: 'orthographic' (default) or 'perspective'.
    width : str, optional
        Width of the viewer. Default is "100%".
    height : str, optional
        Height of the viewer. Default is "400px".
    viewer_outline : bool or str, optional
        Whether to draw outlines around the viewer. Default is False.
    fog : bool, optional
        Whether to apply fog effect. Default is False.
    fog_strength : float, optional
        Strength of the fog effect. Default is 0.5.
    draw_outlines : bool, optional
        Whether to draw outlines around atoms and bonds. Default is False.
    draw_labels : bool, optional
        Whether to draw labels for atoms. Default is False.
    measuring_tool : bool, optional
        Whether to enable measuring tool. Default is False.
    unwrap_molecules : bool, optional
        Whether to unwrap molecules split across periodic boundaries. Default is False.
    spin : bool, optional
        Whether to spin the structure. Default is False.
    spin_axis : tuple[float, float, float] or list[float], optional
        The axis of rotation, in cartesian coordinates. Default is (0.0, 1.0, 0.0).
    spin_speed : float, optional
        The speed of rotation. Default is 2.0. The rotation is clockwise, if an
        anticlockwise rotation is desired, use a negative value.
    multi_traj : bool, optional
        Whether to show trajectory playback controls (play/pause button) for trajectory data (default is True). If False, the play/pause button will be hidden.
    traj_fps : float, optional
        Frames per second for playing trajectory animations. Default is 10.0.
    trajectory_slider : bool, optional
        Whether to show a frame slider for trajectory data. Default is False.
    compute_extra_data : bool, optional
        Whether to compute and display extra data (number of atoms, atomic weight for non-periodic;
        density, volume, number of atoms, and cell vector lengths for periodic structures). Default is False.
    show_help : bool, optional
        Whether to show the help button and enable the 'h' interaction help overlay. Default is True. *(added in v0.2.0)*
    recording_tools : bool, optional
        Whether to show screenshot (PNG) and animation video recording (WebM/MP4) tools in the viewer toolbar. Default is False. *(added in v0.2.0)*
    dpi : int, optional
        Resolution in dots per inch (DPI) for exported screenshots and video recordings. Default is 200. *(added in v0.2.0)*
    record_include_bgd : bool, optional
        Whether to include the viewer's background color in exported screenshots and video recordings (default is False, which produces transparent backgrounds). *(added in v0.2.0)*
    record_include_ui : bool, optional
        Whether to include viewer UI elements (playback controls, info panels, measurement badges, labels) in exported screenshots and video recordings. Default is False. *(added in v0.2.0)*

    Returns
    -------
    marimo.ui.anywidget
        The molecule viewer widget.
    """
    cfg_dict = parse_toml_config(config) if config is not None else {}

    def _resolve(val, key):
        if val is not _UNSET:
            return val
        if key in cfg_dict:
            return cfg_dict[key]
        return DEFAULT_VIEWER_CONFIG[key]

    style = _resolve(style, "style")
    background_color = _resolve(background_color, "background_color")
    show_axes = _resolve(show_axes, "show_axes")
    projection = _resolve(projection, "projection")
    width = _resolve(width, "width")
    height = _resolve(height, "height")
    viewer_outline = _resolve(viewer_outline, "viewer_outline")
    fog = _resolve(fog, "fog")
    fog_strength = _resolve(fog_strength, "fog_strength")
    draw_outlines = _resolve(draw_outlines, "draw_outlines")
    draw_labels = _resolve(draw_labels, "draw_labels")
    measuring_tool = _resolve(measuring_tool, "measuring_tool")
    unwrap_molecules = _resolve(unwrap_molecules, "unwrap_molecules")
    spin = _resolve(spin, "spin")
    spin_axis = _resolve(spin_axis, "spin_axis")
    spin_speed = _resolve(spin_speed, "spin_speed")
    multi_traj = _resolve(multi_traj, "multi_traj")
    traj_fps = _resolve(traj_fps, "traj_fps")
    trajectory_slider = _resolve(trajectory_slider, "trajectory_slider")
    compute_extra_data = _resolve(compute_extra_data, "compute_extra_data")
    show_help = _resolve(show_help, "show_help")
    recording_tools = _resolve(recording_tools, "recording_tools")
    dpi = _resolve(dpi, "dpi")
    record_include_bgd = _resolve(record_include_bgd, "record_include_bgd")
    record_include_ui = _resolve(record_include_ui, "record_include_ui")

    resolved_style = STYLES.get(style, STYLES["vdw"]) if isinstance(style, str) else style
    resolved_bg = resolve_color(background_color)

    is_trajectory = isinstance(data, list)
    frames_data = data if is_trajectory else [data]

    if compute_extra_data:
        from .utils import compute_extra_data as compute_extra_data_func

        for f in frames_data:
            compute_extra_data_func(f)

    if unwrap_molecules:
        from .utils import unwrap_molecules as unwrap_molecules_func

        frames_data = [unwrap_molecules_func(f) for f in frames_data]

    use_vdw = resolved_style.get("use_vdw_radii", False)
    bond_radius = resolved_style.get("bond_radius", 0.0)

    if bond_radius > 0:
        from .utils import compute_bonds

        for f in frames_data:
            if not f.get("bonds"):
                f["bonds"] = compute_bonds(f, use_pbc=True)
    sel_radius_map = VDW_RADII if use_vdw else ATOMIC_RADII
    sel_default_radius = DEFAULT_VDW_RADIUS if use_vdw else DEFAULT_RADIUS

    widget = MoleculeViewerWidget(
        data=frames_data,
        color_map=CPK_COLORS,
        radius_map=sel_radius_map,
        default_color=DEFAULT_COLOR,
        default_radius=sel_default_radius,
        style=resolved_style,
        background_color=resolved_bg,
        show_axes=show_axes,
        projection=projection,
        width=width,
        height=height,
        viewer_outline=viewer_outline,
        fog=fog,
        fog_strength=fog_strength,
        draw_outlines=draw_outlines,
        draw_labels=draw_labels,
        measuring_tool=measuring_tool,
        spin=spin,
        spin_axis=list(spin_axis),
        spin_speed=spin_speed,
        multi_traj=multi_traj,
        traj_fps=traj_fps,
        trajectory_slider=trajectory_slider,
        show_help=show_help,
        recording_tools=recording_tools,
        dpi=dpi,
        record_include_bgd=record_include_bgd,
        record_include_ui=record_include_ui,
    )

    return mo.ui.anywidget(widget)

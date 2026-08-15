from __future__ import annotations

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

            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.autoClear = false; // We need to manage clearing for multiple viewports
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
                btn.style.borderRadius = '4px';
                btn.style.cursor = 'pointer';
                btn.style.padding = '4px';
                btn.style.display = 'flex';
                btn.style.alignItems = 'center';
                btn.style.justifyContent = 'center';
                btn.style.color = '#555';
                btn.style.transition = 'background 0.2s';
                btn.onclick = onClick;
                btn.onmouseover = () => btn.style.background = 'rgba(0,0,0,0.08)';
                btn.onmouseout = () => btn.style.background = 'transparent';
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

            // --- Right Side UI (Container for Measure, Extra Data, Info Panel) ---
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

            // --- Atom Info Panel ---
            const infoPanel = document.createElement('div');
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
            helpBtn.style.backdropFilter = 'blur(10px)';
            helpBtn.style.WebkitBackdropFilter = 'blur(10px)';
            helpBtn.style.borderRadius = '8px';
            helpBtn.style.padding = '8px';
            helpBtn.style.cursor = 'pointer';
            helpBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            helpBtn.style.transition = 'background 0.2s, transform 0.1s';
            helpBtn.title = 'Help & Controls (H)';

            helpBtn.onmouseover = () => { if (!isHelpOpen) { helpBtn.style.background = 'rgba(255,255,255,0.9)'; helpBtn.style.transform = 'scale(1.1)'; } };
            helpBtn.onmouseout = () => { if (!isHelpOpen) { helpBtn.style.background = 'rgba(255,255,255,0.7)'; helpBtn.style.transform = 'scale(1)'; } };
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
                    helpBtn.style.transform = 'scale(1)';
                    return;
                }
                isHelpOpen = (typeof forceState === 'boolean') ? forceState : !isHelpOpen;
                if (isHelpOpen) {
                    updateHelpContent();
                    helpOverlay.style.display = 'block';
                    helpBtn.style.background = '#00acc1';
                    helpBtn.style.color = 'white';
                    helpBtn.style.transform = 'scale(1.1)';
                } else {
                    helpOverlay.style.display = 'none';
                    helpBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                    helpBtn.style.color = '#333';
                    helpBtn.style.transform = 'scale(1)';
                }
            };

            helpBtn.addEventListener('click', () => {
                toggleHelp();
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
            measureBtn.style.backdropFilter = 'blur(10px)';
            measureBtn.style.WebkitBackdropFilter = 'blur(10px)';
            measureBtn.style.borderRadius = '8px';
            measureBtn.style.padding = '8px';
            measureBtn.style.cursor = 'pointer';
            measureBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            measureBtn.style.transition = 'background 0.2s, transform 0.1s';
            measureBtn.title = 'Measure Tool (Distance, Angle, Dihedral)';
            measureBtn.onmouseover = () => { if (!isMeasuring) { measureBtn.style.background = 'rgba(255,255,255,0.9)'; measureBtn.style.transform = 'scale(1.1)'; } };
            measureBtn.onmouseout = () => { if (!isMeasuring) { measureBtn.style.background = 'rgba(255,255,255,0.7)'; measureBtn.style.transform = 'scale(1)'; } };

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
            extraDataContainer.style.flexShrink = '1';
            extraDataContainer.style.minHeight = '0';

            const extraDataBtn = document.createElement('button');
            const listSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>`;
            extraDataBtn.innerHTML = listSvg;
            extraDataBtn.style.color = '#333';
            extraDataBtn.style.background = 'rgba(255, 255, 255, 0.7)';
            extraDataBtn.style.border = 'none';
            extraDataBtn.style.backdropFilter = 'blur(10px)';
            extraDataBtn.style.WebkitBackdropFilter = 'blur(10px)';
            extraDataBtn.style.borderRadius = '8px';
            extraDataBtn.style.padding = '8px';
            extraDataBtn.style.cursor = 'pointer';
            extraDataBtn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            extraDataBtn.style.transition = 'background 0.2s, transform 0.1s';
            extraDataBtn.title = 'Toggle Extra Data';

            let isExtraDataOpen = false;

            extraDataBtn.onmouseover = () => { if (!isExtraDataOpen) { extraDataBtn.style.background = 'rgba(255,255,255,0.9)'; extraDataBtn.style.transform = 'scale(1.1)'; } };
            extraDataBtn.onmouseout = () => { if (!isExtraDataOpen) { extraDataBtn.style.background = 'rgba(255,255,255,0.7)'; extraDataBtn.style.transform = 'scale(1)'; } };

            const extraDataPanel = document.createElement('div');
            extraDataPanel.style.marginTop = '8px';
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
            extraDataPanel.style.overflowY = 'auto';
            extraDataPanel.style.flexShrink = '1';
            extraDataPanel.style.minHeight = '0';

            extraDataContainer.appendChild(extraDataBtn);
            extraDataContainer.appendChild(extraDataPanel);

            // Note: Since infoPanel has margin-top: auto, we want extraData to be above infoPanel in the DOM.
            // rightSideContainer currently has infoPanel appended first.
            // We should insert helpContainer, measureContainer and extraDataContainer BEFORE infoPanel so they appear at the top!
            rightSideContainer.insertBefore(helpContainer, infoPanel);
            rightSideContainer.insertBefore(measureContainer, infoPanel);
            rightSideContainer.insertBefore(extraDataContainer, infoPanel);
            container.appendChild(rightSideContainer);

            extraDataContainer.addEventListener('click', (e) => e.stopPropagation());

            extraDataBtn.addEventListener('click', () => {
                isExtraDataOpen = !isExtraDataOpen;
                if (isExtraDataOpen) {
                    extraDataBtn.style.background = '#00acc1';
                    extraDataBtn.style.color = 'white';
                    extraDataBtn.style.transform = 'scale(1.1)';
                    extraDataPanel.style.display = 'block';
                } else {
                    extraDataBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                    extraDataBtn.style.color = '#333';
                    extraDataBtn.style.transform = 'scale(1)';
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
                    measureBtn.style.transform = 'scale(1.1)';
                    updateMeasurementUI();
                } else {
                    measureBtn.style.background = 'rgba(255, 255, 255, 0.7)';
                    measureBtn.style.color = '#333';
                    measureBtn.style.transform = 'scale(1)';
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
                const cFrame = model.get('current_frame');
                const frames = model.get('data') || [];
                let positions = [];
                let species_list = [];
                if (frames.length > 0 && frames[cFrame]) {
                    positions = frames[cFrame].positions || [];
                    species_list = frames[cFrame].species || [];
                }

                if (idx < 0 || idx >= positions.length) {
                    infoPanel.style.display = 'none';
                    return;
                }

                const pos = positions[idx] || [0, 0, 0];
                const species = species_list[idx] !== undefined ? species_list[idx] : '?';

                infoPanel.innerText = `Index:   ${idx}\nSpecies: ${species}\nPos:     [${pos[0].toFixed(3)}, ${pos[1].toFixed(3)}, ${pos[2].toFixed(3)}]`;
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

            // Handle KeyDown for Help Overlay Toggle
            let isContainerHovered = false;
            container.addEventListener('mouseenter', () => { isContainerHovered = true; });
            container.addEventListener('mouseleave', () => { isContainerHovered = false; });

            const handleKeyDown = (e) => {
                if (!model.get('show_help')) return;
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;

                const isTargetInside = container.contains(e.target) || isContainerHovered || document.activeElement === container;
                if (!isTargetInside) return;

                if ((e.key === 'h' || e.key === 'H') && !e.ctrlKey && !e.metaKey && !e.altKey) {
                    e.preventDefault();
                    toggleHelp();
                } else if (e.key === 'Escape' && isHelpOpen) {
                    e.preventDefault();
                    toggleHelp(false);
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
            }
            animate();

            // Cleanup when cell is deleted or widget is destroyed
            return () => {
                cancelAnimationFrame(animationId);
                resizeObserver.disconnect();
                window.removeEventListener('keydown', handleKeyDown);
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


def view_structure(
    data: dict | list[dict],
    style: str = "ball-and-stick",
    background_color: str = "white",
    show_axes: bool = False,
    projection: str = "orthographic",
    width: str = "100%",
    height: str = "400px",
    viewer_outline: bool | str = False,
    fog: bool = False,
    fog_strength: float = 0.5,
    draw_outlines: bool = False,
    draw_labels: bool = False,
    measuring_tool: bool = False,
    unwrap_molecules: bool = False,
    spin: bool = False,
    spin_axis: tuple[float, float, float] = (0.0, 1.0, 0.0),
    spin_speed: float = 2.0,
    multi_traj: bool = True,
    traj_fps: float = 10.0,
    trajectory_slider: bool = False,
    compute_extra_data: bool = False,
    show_help: bool = True,
) -> mo.ui.anywidget:
    """
    Visualize a molecule or periodic structure in the notebook.

    Parameters
    ----------
    data : dict or list[dict]
        A dictionary with keys 'positions', 'species', 'bonds' (optional), 'unit_cell' (optional),
        'labels' (optional), 'highlight' (optional), 'extra_data' (optional) or a list of such dictionaries
        for a trajectory.
    style : str or dict, optional
        Style options: 'vdw' (default), 'ball-and-stick', 'wireframe', or a custom dictionary.
    background_color : str, optional
        Background color of the viewer.
    show_axes : bool, optional
        Whether to display XYZ axes in the corner.
    projection : str, optional
        Projection type: 'orthographic' (default) or 'perspective'.
    width : str, optional
        Width of the viewer.
    height : str, optional
        Height of the viewer.
    viewer_outline : bool or str, optional
        Whether to draw outlines around the viewer.
    fog : bool, optional
        Whether to apply fog effect.
    fog_strength : float, optional
        Strength of the fog effect.
    draw_outlines : bool, optional
        Whether to draw outlines around atoms and bonds.
    draw_labels : bool, optional
        Whether to draw labels for atoms.
    measuring_tool : bool, optional
        Whether to enable measuring tool.
    unwrap_molecules : bool, optional
        Whether to unwrap molecules split across periodic boundaries.
    spin : bool, optional
        Whether to spin the structure.
    spin_axis : tuple[float, float, float], optional
        The axis of rotation, in cartesian coordinates. Default is (0.0, 1.0, 0.0).
    spin_speed : float, optional
        The speed of rotation. Default is 2.0. The rotation is clockwise, if an
        anticlockwise rotation is desired, use a negative value.
    multi_traj : bool, optional
        Whether to show trajectory playback controls (play/pause button) for trajectory data (default is True). If False, the play/pause button will be hidden.
    traj_fps : float, optional
        Frames per second for playing trajectory animations (default is 10.0).
    trajectory_slider : bool, optional
        Whether to show a frame slider for trajectory data (default is False).
    compute_extra_data : bool, optional
        Whether to compute and display extra data (number of atoms, atomic weight for non-periodic;
        density, volume, number of atoms, and cell vector lengths for periodic structures). Default is False.
    show_help : bool, optional
        Whether to show the help button and enable the 'h' interaction help overlay (default is True).

    Returns
    -------
    marimo.ui.anywidget
        The molecule viewer widget.
    """
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
    )

    return mo.ui.anywidget(widget)

import anywidget
import traitlets
import marimo as mo
from .color_utils import resolve_color

class MoleculeViewerWidget(anywidget.AnyWidget):
    _esm = """
    import * as THREE from 'https://esm.sh/three@0.160.0';
    import { TrackballControls } from 'https://esm.sh/three@0.160.0/addons/controls/TrackballControls.js';

    export default {
        render({ model, el }) {
            // Container setup
            const container = document.createElement('div');
            container.style.width = '100%';
            container.style.height = '400px';
            container.style.display = 'block';
            container.style.backgroundColor = model.get('background_color') || '#ffffff';
            container.style.overflow = 'hidden';
            el.appendChild(container);

            // Three.js setup
            const scene = new THREE.Scene();
            
            // Add lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(10, 20, 10);
            scene.add(dirLight);

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
            
            let atomMesh = null; // InstancedMesh for atoms
            let bondMesh = null; // InstancedMesh for bonds
            let cellGroup = null; // Group containing cell lines and labels
            const dummy = new THREE.Object3D();
            const colorObj = new THREE.Color();
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();
            const yAxis = new THREE.Vector3(0, 1, 0);

            function updateScene() {
                const atoms = model.get('atoms') || [];
                let bonds = model.get('bonds') || [];
                const style = model.get('style') || 'vdw';
                
                const numAtoms = atoms.length;
                
                // Clear old meshes
                if (atomMesh) { scene.remove(atomMesh); atomMesh.dispose(); atomMesh = null; }
                if (bondMesh) { scene.remove(bondMesh); bondMesh.dispose(); bondMesh = null; }
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

                // Auto-compute bonds if not provided and style needs them
                if (bonds.length === 0 && (style === 'ball-and-stick' || style === 'wireframe')) {
                    bonds = [];
                    for(let i=0; i<numAtoms; i++) {
                        for(let j=i+1; j<numAtoms; j++) {
                            const a = atoms[i], b = atoms[j];
                            const dx = a.position[0] - b.position[0];
                            const dy = a.position[1] - b.position[1];
                            const dz = a.position[2] - b.position[2];
                            const dist = Math.hypot(dx, dy, dz);
                            // 1.3 is a standard tolerance for covalent radii bonding
                            if (dist > 0.1 && dist < (a.radius + b.radius) * 1.3) {
                                bonds.push({source: i, target: j});
                            }
                        }
                    }
                }

                // Determine styling parameters
                let showBonds = false;
                let bondRadius = 0.15;
                
                if (style === 'ball-and-stick') {
                    showBonds = true;
                    bondRadius = 0.15;
                } else if (style === 'wireframe') {
                    showBonds = true;
                    bondRadius = 0.05;
                } else {
                    // vdw
                    showBonds = false;
                }

                // --- ATOMS ---
                atomMesh = new THREE.InstancedMesh(sphereGeometry, sphereMaterial, numAtoms);
                let centerSum = new THREE.Vector3(0, 0, 0);

                for (let i = 0; i < numAtoms; i++) {
                    const a = atoms[i];
                    const pos = a.position || [0, 0, 0];
                    const col = a.color || [1, 1, 1];
                    let rad = a.radius || 1.0;
                    if (style === 'ball-and-stick') {
                        // Standard size 0.3, hydrogen (<0.4) slightly smaller at 0.2
                        rad = (rad < 0.4) ? 0.2 : 0.3;
                    } else if (style === 'wireframe') {
                        // Match bond width exactly to prevent discontinuities
                        rad = bondRadius;
                    }

                    dummy.position.set(pos[0], pos[1], pos[2]);
                    dummy.scale.set(rad, rad, rad);
                    // Reset rotation just in case
                    dummy.quaternion.identity();
                    dummy.updateMatrix();
                    atomMesh.setMatrixAt(i, dummy.matrix);

                    colorObj.setRGB(col[0], col[1], col[2]);
                    atomMesh.setColorAt(i, colorObj);
                    
                    centerSum.add(dummy.position);
                }
                
                atomMesh.instanceMatrix.needsUpdate = true;
                if (atomMesh.instanceColor) atomMesh.instanceColor.needsUpdate = true;
                scene.add(atomMesh);

                // --- BONDS ---
                if (showBonds && bonds.length > 0) {
                    bondMesh = new THREE.InstancedMesh(cylinderGeometry, cylinderMaterial, bonds.length * 2);
                    const vA = new THREE.Vector3();
                    const vB = new THREE.Vector3();
                    const vDir = new THREE.Vector3();
                    const vMid = new THREE.Vector3();
                    
                    for (let i = 0; i < bonds.length; i++) {
                        const b = bonds[i];
                        const atomA = atoms[b.source];
                        const atomB = atoms[b.target];
                        
                        vA.fromArray(atomA.position || [0,0,0]);
                        vB.fromArray(atomB.position || [0,0,0]);
                        vMid.copy(vA).lerp(vB, 0.5);
                        
                        const distance = vA.distanceTo(vMid);
                        vDir.subVectors(vB, vA).normalize();
                        
                        // First half (Atom A to Midpoint)
                        dummy.position.copy(vA).lerp(vMid, 0.5);
                        dummy.scale.set(bondRadius, distance, bondRadius);
                        dummy.quaternion.setFromUnitVectors(yAxis, vDir);
                        dummy.updateMatrix();
                        bondMesh.setMatrixAt(i * 2, dummy.matrix);
                        
                        const colA = atomA.color || [1,1,1];
                        colorObj.setRGB(colA[0], colA[1], colA[2]);
                        bondMesh.setColorAt(i * 2, colorObj);
                        
                        // Second half (Midpoint to Atom B)
                        dummy.position.copy(vMid).lerp(vB, 0.5);
                        dummy.scale.set(bondRadius, distance, bondRadius);
                        // quaternion stays the same since direction is the same
                        dummy.updateMatrix();
                        bondMesh.setMatrixAt(i * 2 + 1, dummy.matrix);
                        
                        const colB = atomB.color || [1,1,1];
                        colorObj.setRGB(colB[0], colB[1], colB[2]);
                        bondMesh.setColorAt(i * 2 + 1, colorObj);
                    }
                    bondMesh.instanceMatrix.needsUpdate = true;
                    if (bondMesh.instanceColor) bondMesh.instanceColor.needsUpdate = true;
                    scene.add(bondMesh);
                }

                // --- UNIT CELL ---
                const unitCell = model.get('unit_cell');
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
                controls.target.copy(sceneCenter);
                
                let maxDist = 0;
                if (cellCenter) {
                    // Base maxDist on the distance from cell center to the origin (half the main diagonal)
                    maxDist = cellCenter.length();
                } else if (numAtoms > 0) {
                    for (let i = 0; i < numAtoms; i++) {
                        const pos = new THREE.Vector3().fromArray(atoms[i].position);
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
            }

            // Watch for changes from Python
            model.on("change:atoms", updateScene);
            model.on("change:bonds", updateScene);
            model.on("change:style", updateScene);
            model.on("change:unit_cell", updateScene);
            model.on("change:background_color", () => {
                container.style.backgroundColor = model.get('background_color');
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
                    updateScene();
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

            // Handle Click (Picking or Axis Snapping)
            container.addEventListener('click', (event) => {
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
                        model.set("selected_atom_index", instanceId);
                        model.save_changes();
                    } else {
                        model.set("selected_atom_index", -1);
                        model.save_changes();
                    }
                }
            });

            // Render Loop
            let animationId;
            function animate() {
                animationId = requestAnimationFrame(animate);
                controls.update();
                
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
                if (atomMesh) {
                    atomMesh.dispose();
                    scene.remove(atomMesh);
                }
                renderer.dispose();
            };
        }
    }
    """
    atoms = traitlets.List().tag(sync=True)
    bonds = traitlets.List(default_value=[]).tag(sync=True)
    unit_cell = traitlets.List(default_value=[]).tag(sync=True)
    selected_atom_index = traitlets.Int(-1).tag(sync=True)
    background_color = traitlets.Unicode('#ffffff').tag(sync=True)
    style = traitlets.Unicode('vdw').tag(sync=True) # options: 'vdw', 'ball-and-stick', 'wireframe'
    show_axes = traitlets.Bool(False).tag(sync=True)
    projection = traitlets.Unicode('perspective').tag(sync=True) # 'perspective' or 'orthographic'

def view_molecule(atoms, bonds=None, unit_cell=None, style="vdw", background_color="white", show_axes=False, projection="perspective"):
    """
    Visualize a list of atoms using WebGL (Three.js).
    atoms format: [{"position": [x, y, z], "color": [r, g, b], "radius": r}, ...]
    bonds format: [{"source": i, "target": j}, ...]
    unit_cell format: [[v1x, v1y, v1z], [v2x, v2y, v2z], [v3x, v3y, v3z]]
    style options: 'vdw' (default), 'ball-and-stick', 'wireframe'
    show_axes: bool, whether to display XYZ axes in the corner
    projection: 'perspective' (default) or 'orthographic'
    """
    resolved_bg = resolve_color(background_color)
    widget = MoleculeViewerWidget(
        atoms=atoms,
        bonds=bonds or [],
        unit_cell=unit_cell or [],
        style=style,
        background_color=resolved_bg,
        show_axes=show_axes,
        projection=projection
    )
    return mo.ui.anywidget(widget)

import anywidget
import traitlets
import marimo as mo
from .color_utils import resolve_color

class MoleculeViewerWidget(anywidget.AnyWidget):
    _esm = """
    import * as THREE from 'https://esm.sh/three@0.160.0';
    import { OrbitControls } from 'https://esm.sh/three@0.160.0/addons/controls/OrbitControls.js';

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

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            
            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.1;

            // Geometry and Material for Atoms
            // We use a high segment count for smooth spheres, but InstancedMesh keeps it incredibly fast
            const sphereGeometry = new THREE.SphereGeometry(1, 32, 32);
            const sphereMaterial = new THREE.MeshPhongMaterial({ 
                color: 0xffffff,
                shininess: 60
            });
            const cylinderGeometry = new THREE.CylinderGeometry(1, 1, 1, 16);
            // Cylinder is along Y axis by default, length 1.
            const cylinderMaterial = new THREE.MeshPhongMaterial({
                color: 0xcccccc,
                shininess: 60
            });
            
            let atomMesh = null; // InstancedMesh for atoms
            let bondMesh = null; // InstancedMesh for bonds
            
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

                if (numAtoms === 0) return;

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
                    bondMesh = new THREE.InstancedMesh(cylinderGeometry, cylinderMaterial, bonds.length);
                    const vA = new THREE.Vector3();
                    const vB = new THREE.Vector3();
                    const vDir = new THREE.Vector3();
                    
                    for (let i = 0; i < bonds.length; i++) {
                        const b = bonds[i];
                        const a1 = atoms[b.source].position;
                        const a2 = atoms[b.target].position;
                        
                        vA.set(a1[0], a1[1], a1[2]);
                        vB.set(a2[0], a2[1], a2[2]);
                        
                        const distance = vA.distanceTo(vB);
                        const center = vA.clone().lerp(vB, 0.5);
                        
                        dummy.position.copy(center);
                        // Cylinder geometry length is 1, so scale Y to distance
                        dummy.scale.set(bondRadius, distance, bondRadius);
                        
                        vDir.subVectors(vB, vA).normalize();
                        dummy.quaternion.setFromUnitVectors(yAxis, vDir);
                        dummy.updateMatrix();
                        
                        bondMesh.setMatrixAt(i, dummy.matrix);
                        // Optional: bonds take color of atoms? Here they are just gray.
                        // colorObj.setHex(0xcccccc);
                        // bondMesh.setColorAt(i, colorObj);
                    }
                    bondMesh.instanceMatrix.needsUpdate = true;
                    scene.add(bondMesh);
                }

                // Auto-center and fit camera
                centerSum.divideScalar(numAtoms);
                controls.target.copy(centerSum);
                
                let maxDist = 0;
                for (let i = 0; i < numAtoms; i++) {
                    const pos = new THREE.Vector3().fromArray(atoms[i].position);
                    const dist = pos.distanceTo(centerSum);
                    if (dist > maxDist) maxDist = dist;
                }
                
                const cameraDist = Math.max(10, maxDist * 3);
                camera.position.set(centerSum.x, centerSum.y, centerSum.z + cameraDist);
                controls.update();
            }

            // Watch for changes from Python
            model.on("change:atoms", updateScene);
            model.on("change:bonds", updateScene);
            model.on("change:style", updateScene);
            model.on("change:background_color", () => {
                container.style.backgroundColor = model.get('background_color');
            });
            updateScene();

            // Handle Resize
            const resizeObserver = new ResizeObserver(() => {
                if (container.clientWidth === 0 || container.clientHeight === 0) return;
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });
            resizeObserver.observe(container);

            // Handle Click (Picking)
            container.addEventListener('click', (event) => {
                const rect = container.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / container.clientWidth) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / container.clientHeight) * 2 + 1;

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
                renderer.render(scene, camera);
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
    selected_atom_index = traitlets.Int(-1).tag(sync=True)
    background_color = traitlets.Unicode('#ffffff').tag(sync=True)
    style = traitlets.Unicode('vdw').tag(sync=True) # options: 'vdw', 'ball-and-stick', 'wireframe'

def view_molecule(atoms, bonds=None, style="vdw", background_color="white"):
    """
    Visualize a list of atoms using WebGL (Three.js).
    atoms format: [{"position": [x, y, z], "color": [r, g, b], "radius": r}, ...]
    bonds format: [{"source": i, "target": j}, ...]
    style options: 'vdw' (default), 'ball-and-stick', 'wireframe'
    """
    resolved_bg = resolve_color(background_color)
    widget = MoleculeViewerWidget(
        atoms=atoms,
        bonds=bonds or [],
        style=style,
        background_color=resolved_bg
    )
    return mo.ui.anywidget(widget)

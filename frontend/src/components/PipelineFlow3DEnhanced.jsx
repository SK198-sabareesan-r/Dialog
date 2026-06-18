import { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Sphere, Environment, PerspectiveCamera, MeshDistortMaterial, Stars } from '@react-three/drei';
import * as THREE from 'three';

// Enhanced 3D Node Component with glow effect
const Node3D = ({ position, color, label, scale = 1, isActive = false }) => {
  const meshRef = useRef();
  const glowRef = useRef();
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005;
      if (isActive) {
        const pulse = Math.sin(state.clock.elapsedTime * 3) * 0.2 + 1;
        meshRef.current.scale.setScalar(scale * pulse);
        if (glowRef.current) {
          glowRef.current.scale.setScalar(scale * pulse * 1.3);
        }
      } else if (hovered) {
        meshRef.current.scale.setScalar(scale * 1.1);
      } else {
        meshRef.current.scale.setScalar(scale);
      }
    }
  });

  return (
    <group position={position}>
      {/* Outer glow sphere */}
      <Sphere ref={glowRef} args={[0.55, 32, 32]}>
        <meshBasicMaterial color={color} transparent opacity={isActive ? 0.3 : 0.1} />
      </Sphere>

      {/* Main node */}
      <Sphere
        ref={meshRef}
        args={[0.4, 32, 32]}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <MeshDistortMaterial
          color={color}
          attach="material"
          distort={0.3}
          speed={2}
          roughness={0.2}
          metalness={0.8}
        />
      </Sphere>

      {/* Label */}
      <Text
        position={[0, -0.8, 0]}
        fontSize={0.15}
        color="white"
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.02}
        outlineColor="#000000"
      >
        {label}
      </Text>

      {/* Point light for active nodes */}
      {isActive && (
        <pointLight position={[0, 0, 0]} intensity={2} color={color} distance={5} />
      )}
    </group>
  );
};

// Animated connection line
const ConnectionLine = ({ start, end, isActive = false }) => {
  const lineRef = useRef();
  const particlesRef = useRef();

  useFrame((state) => {
    if (particlesRef.current && isActive) {
      particlesRef.current.position.x = Math.sin(state.clock.elapsedTime * 2) * 0.1;
      particlesRef.current.position.y = Math.cos(state.clock.elapsedTime * 2) * 0.1;
    }
  });

  const points = [];
  const numPoints = 50;
  for (let i = 0; i <= numPoints; i++) {
    const t = i / numPoints;
    const x = start[0] + (end[0] - start[0]) * t;
    const y = start[1] + (end[1] - start[1]) * t + Math.sin(t * Math.PI) * 0.3;
    const z = start[2] + (end[2] - start[2]) * t;
    points.push(new THREE.Vector3(x, y, z));
  }

  const curve = new THREE.CatmullRomCurve3(points);
  const lineGeometry = new THREE.TubeGeometry(curve, 50, 0.02, 8, false);

  return (
    <group>
      <mesh ref={lineRef} geometry={lineGeometry}>
        <meshStandardMaterial
          color={isActive ? '#00ffff' : '#667eea'}
          emissive={isActive ? '#00ffff' : '#667eea'}
          emissiveIntensity={isActive ? 0.5 : 0.2}
          transparent
          opacity={isActive ? 0.9 : 0.4}
        />
      </mesh>

      {/* Flowing particles */}
      {isActive && (
        <Sphere ref={particlesRef} args={[0.05, 8, 8]} position={start}>
          <meshBasicMaterial color="#00ffff" />
        </Sphere>
      )}
    </group>
  );
};

// Main 3D Pipeline Scene
const PipelineScene = ({ activeStage }) => {
  const groupRef = useRef();

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.1) * 0.1;
    }
  });

  const nodes = {
    sources: [
      { pos: [-3, 3, 0], label: 'Web UI', color: '#3b82f6' },
      { pos: [-1, 3, 0], label: 'Drive', color: '#10b981' },
      { pos: [1, 3, 0], label: 'Repo', color: '#f59e0b' },
      { pos: [3, 3, 0], label: 'S3', color: '#06b6d4' },
    ],
    rawZone: { pos: [0, 1.5, 0], label: 'S3 Raw', color: '#60a5fa' },
    stepFunctions: { pos: [0, 0, 0], label: 'Step Functions', color: '#a78bfa' },
    formatProcessor: { pos: [0, -1.5, 0], label: 'Format Processor', color: '#f97316' },
    handlers: [
      { pos: [-3, -3, 0], label: 'Parser', color: '#ef4444' },
      { pos: [-1, -3, 0], label: 'Textract', color: '#8b5cf6' },
      { pos: [1, -3, 0], label: 'Transcribe', color: '#14b8a6' },
      { pos: [3, -3, 0], label: 'Excel', color: '#22c55e' },
    ],
    processed: { pos: [-2.5, -4.5, 0], label: 'S3 Processed', color: '#60a5fa' },
    kb: { pos: [-2.5, -6, 0], label: 'Knowledge Base', color: '#8b5cf6' },
    opensearch: { pos: [-2.5, -7.5, 0], label: 'OpenSearch', color: '#10b981' },
    dlq: { pos: [2.5, -4.5, 0], label: 'DLQ', color: '#ef4444' },
  };

  return (
    <group ref={groupRef}>
      {/* Source nodes */}
      {nodes.sources.map((source, idx) => (
        <Node3D
          key={`source-${idx}`}
          position={source.pos}
          color={source.color}
          label={source.label}
          scale={0.8}
          isActive={activeStage === 'sources'}
        />
      ))}

      {/* Main pipeline nodes */}
      <Node3D
        position={nodes.rawZone.pos}
        color={nodes.rawZone.color}
        label={nodes.rawZone.label}
        scale={1.2}
        isActive={activeStage === 'raw'}
      />

      <Node3D
        position={nodes.stepFunctions.pos}
        color={nodes.stepFunctions.color}
        label={nodes.stepFunctions.label}
        scale={1.2}
        isActive={activeStage === 'orchestration'}
      />

      <Node3D
        position={nodes.formatProcessor.pos}
        color={nodes.formatProcessor.color}
        label={nodes.formatProcessor.label}
        scale={1.2}
        isActive={activeStage === 'bda'}
      />

      {/* Handler nodes */}
      {nodes.handlers.map((handler, idx) => (
        <Node3D
          key={`handler-${idx}`}
          position={handler.pos}
          color={handler.color}
          label={handler.label}
          scale={0.9}
          isActive={activeStage === 'bda'}
        />
      ))}

      <Node3D
        position={nodes.processed.pos}
        color={nodes.processed.color}
        label={nodes.processed.label}
        scale={1}
        isActive={activeStage === 'processed'}
      />

      <Node3D
        position={nodes.kb.pos}
        color={nodes.kb.color}
        label={nodes.kb.label}
        scale={1}
        isActive={activeStage === 'kb'}
      />

      <Node3D
        position={nodes.opensearch.pos}
        color={nodes.opensearch.color}
        label={nodes.opensearch.label}
        scale={1}
        isActive={activeStage === 'opensearch'}
      />

      <Node3D
        position={nodes.dlq.pos}
        color={nodes.dlq.color}
        label={nodes.dlq.label}
        scale={0.9}
        isActive={activeStage === 'dlq'}
      />

      {/* Connection lines */}
      {nodes.sources.map((source, idx) => (
        <ConnectionLine
          key={`conn-source-${idx}`}
          start={source.pos}
          end={nodes.rawZone.pos}
          isActive={activeStage === 'sources'}
        />
      ))}

      <ConnectionLine
        start={nodes.rawZone.pos}
        end={nodes.stepFunctions.pos}
        isActive={activeStage === 'raw'}
      />

      <ConnectionLine
        start={nodes.stepFunctions.pos}
        end={nodes.formatProcessor.pos}
        isActive={activeStage === 'orchestration'}
      />

      {nodes.handlers.map((handler, idx) => (
        <ConnectionLine
          key={`conn-handler-${idx}`}
          start={nodes.formatProcessor.pos}
          end={handler.pos}
          isActive={activeStage === 'bda'}
        />
      ))}

      <ConnectionLine
        start={nodes.handlers[0].pos}
        end={nodes.processed.pos}
        isActive={activeStage === 'processed'}
      />

      <ConnectionLine
        start={nodes.processed.pos}
        end={nodes.kb.pos}
        isActive={activeStage === 'kb'}
      />

      <ConnectionLine
        start={nodes.kb.pos}
        end={nodes.opensearch.pos}
        isActive={activeStage === 'opensearch'}
      />

      <ConnectionLine
        start={nodes.formatProcessor.pos}
        end={nodes.dlq.pos}
        isActive={activeStage === 'dlq'}
      />
    </group>
  );
};

const PipelineFlow3DEnhanced = ({ activeStage }) => {
  return (
    <Canvas style={{ background: 'transparent' }}>
      <PerspectiveCamera makeDefault position={[0, 0, 15]} fov={50} />

      {/* Lighting */}
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#ffffff" />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#667eea" />
      <pointLight position={[0, 0, 10]} intensity={0.5} color="#764ba2" />

      {/* Starfield background */}
      <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />

      {/* Main scene */}
      <PipelineScene activeStage={activeStage} />

      {/* Environment for reflections */}
      <Environment preset="city" />

      {/* Camera controls */}
      <OrbitControls
        enableZoom={true}
        enablePan={true}
        enableRotate={true}
        autoRotate={false}
        maxDistance={25}
        minDistance={8}
      />
    </Canvas>
  );
};

export default PipelineFlow3DEnhanced;

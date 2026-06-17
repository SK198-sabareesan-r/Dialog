import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Box, Sphere } from '@react-three/drei';
import * as THREE from 'three';

// Animated Node Component
const Node = ({ position, color, label, scale = 1, isActive = false }) => {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.01;
      if (isActive) {
        meshRef.current.scale.setScalar(
          scale + Math.sin(state.clock.elapsedTime * 2) * 0.1
        );
      }
    }
  });

  return (
    <group position={position}>
      <Box
        ref={meshRef}
        args={[1.2, 0.8, 0.4]}
        scale={hovered ? scale * 1.1 : scale}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <meshStandardMaterial
          color={hovered ? '#ffffff' : color}
          emissive={isActive ? color : '#000000'}
          emissiveIntensity={isActive ? 0.5 : 0}
          metalness={0.6}
          roughness={0.2}
        />
      </Box>
      <Text
        position={[0, 0, 0.3]}
        fontSize={0.15}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </Text>
    </group>
  );
};

// Connection Line Component
const ConnectionLine = ({ start, end, isActive = false }) => {
  const points = [new THREE.Vector3(...start), new THREE.Vector3(...end)];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);

  return (
    <line geometry={geometry}>
      <lineBasicMaterial
        color={isActive ? '#10b981' : '#64748b'}
        linewidth={isActive ? 3 : 1}
      />
    </line>
  );
};

// Animated Particle Flow
const DataParticle = ({ path, speed = 1 }) => {
  const particleRef = useRef();
  const [progress, setProgress] = useState(0);

  useFrame((state, delta) => {
    setProgress((prev) => (prev + delta * speed) % 1);
    if (particleRef.current && path.length > 1) {
      const currentIndex = Math.floor(progress * (path.length - 1));
      const nextIndex = Math.min(currentIndex + 1, path.length - 1);
      const localProgress = (progress * (path.length - 1)) % 1;

      const current = new THREE.Vector3(...path[currentIndex]);
      const next = new THREE.Vector3(...path[nextIndex]);
      particleRef.current.position.lerpVectors(current, next, localProgress);
    }
  });

  return (
    <Sphere ref={particleRef} args={[0.1, 16, 16]}>
      <meshStandardMaterial color="#10b981" emissive="#10b981" emissiveIntensity={1} />
    </Sphere>
  );
};

const PipelineFlow3D = ({ activeStage = null }) => {
  // Pipeline node positions
  const nodes = {
    sources: [
      { pos: [-4, 3, 0], label: 'Web UI', color: '#f1efe8' },
      { pos: [-2, 3, 0], label: 'Shared Drive', color: '#f1efe8' },
      { pos: [0, 3, 0], label: 'File Repo', color: '#f1efe8' },
      { pos: [2, 3, 0], label: 'S3 Direct', color: '#f1efe8' },
    ],
    rawZone: { pos: [0, 1.5, 0], label: 'S3 Raw Zone', color: '#e6f1fb' },
    stepFunctions: { pos: [0, 0, 0], label: 'Step Functions', color: '#f1efe8' },
    bda: { pos: [0, -1.5, 0], label: 'BDA Parser', color: '#faece7' },
    processed: { pos: [-2.5, -3, 0], label: 'S3 Processed', color: '#e6f1fb' },
    dlq: { pos: [2.5, -3, 0], label: 'DLQ', color: '#fcebeb' },
    kb: { pos: [-2.5, -4.5, 0], label: 'Knowledge Base', color: '#eeeefd' },
    opensearch: { pos: [-2.5, -6, 0], label: 'OpenSearch', color: '#e1f5ee' },
    retrieval: { pos: [-2.5, -7.5, 0], label: 'Retrieval + IAM', color: '#eeeefd' },
  };

  // Data flow paths (for future animation features)
  // const flowPaths = [
  //   [nodes.sources[0].pos, nodes.rawZone.pos],
  //   [nodes.sources[1].pos, nodes.rawZone.pos],
  //   [nodes.sources[2].pos, nodes.rawZone.pos],
  //   [nodes.sources[3].pos, nodes.rawZone.pos],
  //   [nodes.rawZone.pos, nodes.stepFunctions.pos, nodes.bda.pos],
  //   [nodes.bda.pos, nodes.processed.pos, nodes.kb.pos, nodes.opensearch.pos, nodes.retrieval.pos],
  //   [nodes.bda.pos, nodes.dlq.pos],
  // ];

  return (
    <Canvas
      camera={{ position: [0, 0, 15], fov: 50 }}
      style={{ background: 'transparent' }}
    >
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#667eea" />

      {/* Source Nodes */}
      {nodes.sources.map((node, idx) => (
        <Node
          key={`source-${idx}`}
          position={node.pos}
          color={node.color}
          label={node.label}
          isActive={activeStage === 'sources'}
        />
      ))}

      {/* Pipeline Nodes */}
      <Node
        position={nodes.rawZone.pos}
        color={nodes.rawZone.color}
        label={nodes.rawZone.label}
        scale={1.5}
        isActive={activeStage === 'raw'}
      />
      <Node
        position={nodes.stepFunctions.pos}
        color={nodes.stepFunctions.color}
        label={nodes.stepFunctions.label}
        isActive={activeStage === 'orchestration'}
      />
      <Node
        position={nodes.bda.pos}
        color={nodes.bda.color}
        label={nodes.bda.label}
        scale={1.3}
        isActive={activeStage === 'bda'}
      />
      <Node
        position={nodes.processed.pos}
        color={nodes.processed.color}
        label={nodes.processed.label}
        isActive={activeStage === 'processed'}
      />
      <Node
        position={nodes.dlq.pos}
        color={nodes.dlq.color}
        label={nodes.dlq.label}
        isActive={activeStage === 'dlq'}
      />
      <Node
        position={nodes.kb.pos}
        color={nodes.kb.color}
        label={nodes.kb.label}
        isActive={activeStage === 'kb'}
      />
      <Node
        position={nodes.opensearch.pos}
        color={nodes.opensearch.color}
        label={nodes.opensearch.label}
        scale={1.2}
        isActive={activeStage === 'opensearch'}
      />
      <Node
        position={nodes.retrieval.pos}
        color={nodes.retrieval.color}
        label={nodes.retrieval.label}
        isActive={activeStage === 'retrieval'}
      />

      {/* Connection Lines */}
      {nodes.sources.map((source, idx) => (
        <ConnectionLine
          key={`line-source-${idx}`}
          start={source.pos}
          end={nodes.rawZone.pos}
          isActive={activeStage === 'sources'}
        />
      ))}
      <ConnectionLine start={nodes.rawZone.pos} end={nodes.stepFunctions.pos} />
      <ConnectionLine start={nodes.stepFunctions.pos} end={nodes.bda.pos} />
      <ConnectionLine start={nodes.bda.pos} end={nodes.processed.pos} isActive={activeStage === 'processed'} />
      <ConnectionLine start={nodes.bda.pos} end={nodes.dlq.pos} isActive={activeStage === 'dlq'} />
      <ConnectionLine start={nodes.processed.pos} end={nodes.kb.pos} />
      <ConnectionLine start={nodes.kb.pos} end={nodes.opensearch.pos} />
      <ConnectionLine start={nodes.opensearch.pos} end={nodes.retrieval.pos} />

      {/* Animated Data Particles */}
      {activeStage === 'sources' && (
        <>
          <DataParticle path={[nodes.sources[0].pos, nodes.rawZone.pos]} speed={0.5} />
          <DataParticle path={[nodes.sources[2].pos, nodes.rawZone.pos]} speed={0.6} />
        </>
      )}
      {activeStage === 'bda' && (
        <DataParticle
          path={[nodes.bda.pos, nodes.processed.pos, nodes.kb.pos]}
          speed={0.4}
        />
      )}

      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        autoRotate={!activeStage}
        autoRotateSpeed={0.5}
      />
    </Canvas>
  );
};

export default PipelineFlow3D;

import { Suspense, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stage, useGLTF } from "@react-three/drei";
import * as THREE from "three";

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  useEffect(() => {
    // FrontSide, non DoubleSide: un modello con le normali girate deve
    // vedersi subito, non tre passaggi dopo.
    scene.traverse((o: any) => {
      if (o.isMesh && o.material) o.material.side = THREE.FrontSide;
    });
  }, [scene]);
  return <primitive object={scene} />;
}

export function Viewport({ url }: { url: string | null }) {
  return (
    <Canvas camera={{ fov: 28, position: [0, 80, 380] }} dpr={[1, 2]}>
      <color attach="background" args={["#f2efeb"]} />
      <ambientLight intensity={0.8} />
      <directionalLight position={[-3, 6, 7]} intensity={0.5} />
      <directionalLight position={[5, 2, -4]} intensity={0.2} />
      <Suspense fallback={null}>
        {url && (
          <Stage environment={null} intensity={0.35} adjustCamera={1.15}>
            <Model url={url} />
          </Stage>
        )}
      </Suspense>
      <OrbitControls makeDefault enableDamping />
    </Canvas>
  );
}

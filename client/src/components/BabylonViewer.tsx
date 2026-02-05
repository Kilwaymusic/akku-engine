import { useEffect, useRef, useState } from "react";
import { Loader2, Monitor, AlertTriangle } from "lucide-react";

interface BabylonViewerProps {
  modelUrl: string | null;
  isLoading?: boolean;
  wireframe?: boolean;
}

function checkWebGLSupport(): boolean {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    return !!gl;
  } catch (e) {
    return false;
  }
}

export function BabylonViewer({ modelUrl, isLoading, wireframe = false }: BabylonViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<any>(null);
  const sceneRef = useRef<any>(null);
  const [loadingModel, setLoadingModel] = useState(false);
  const [webglSupported, setWebglSupported] = useState<boolean | null>(null);
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    const supported = checkWebGLSupport();
    setWebglSupported(supported);
    
    if (!supported || !canvasRef.current) return;

    let engine: any = null;
    let scene: any = null;

    const initBabylon = async () => {
      try {
        const { Engine, Scene, ArcRotateCamera, HemisphericLight, Vector3, Color4, DirectionalLight, Color3 } = await import("@babylonjs/core");
        await import("@babylonjs/loaders/glTF");
        
        if (!canvasRef.current) return;

        engine = new Engine(canvasRef.current, true, {
          preserveDrawingBuffer: true,
          stencil: true,
        });
        engineRef.current = engine;

        scene = new Scene(engine);
        sceneRef.current = scene;
        scene.clearColor = new Color4(0.08, 0.08, 0.12, 1);

        const camera = new ArcRotateCamera(
          "camera",
          Math.PI / 2,
          Math.PI / 2.5,
          5,
          Vector3.Zero(),
          scene
        );
        camera.attachControl(canvasRef.current, true);
        camera.wheelPrecision = 50;
        camera.lowerRadiusLimit = 2;
        camera.upperRadiusLimit = 15;

        const hemisphericLight = new HemisphericLight(
          "hemisphericLight",
          new Vector3(0, 1, 0),
          scene
        );
        hemisphericLight.intensity = 0.7;
        hemisphericLight.groundColor = new Color3(0.2, 0.2, 0.3);

        const directionalLight = new DirectionalLight(
          "directionalLight",
          new Vector3(-1, -2, -1),
          scene
        );
        directionalLight.intensity = 0.5;

        engine.runRenderLoop(() => {
          scene.render();
        });

        const handleResize = () => {
          engine.resize();
        };
        window.addEventListener("resize", handleResize);

        return () => {
          window.removeEventListener("resize", handleResize);
        };
      } catch (error) {
        console.error("Failed to initialize Babylon.js:", error);
        setInitError(error instanceof Error ? error.message : "Failed to initialize 3D viewer");
      }
    };

    initBabylon();

    return () => {
      if (engineRef.current) {
        engineRef.current.dispose();
        engineRef.current = null;
        sceneRef.current = null;
      }
    };
  }, [webglSupported]);

  useEffect(() => {
    if (!modelUrl || !sceneRef.current || !webglSupported) return;

    const loadModel = async () => {
      const scene = sceneRef.current;
      setLoadingModel(true);

      try {
        const { SceneLoader } = await import("@babylonjs/core/Loading/sceneLoader");
        const { Vector3, StandardMaterial } = await import("@babylonjs/core");
        const { ArcRotateCamera } = await import("@babylonjs/core");

        scene.meshes.forEach((mesh: any) => {
          if (mesh.name !== "camera" && mesh.name !== "light") {
            mesh.dispose();
          }
        });

        const result = await SceneLoader.ImportMeshAsync("", modelUrl, "", scene);
        const meshes = result.meshes;
        
        // Apply wireframe to all meshes
        meshes.forEach((mesh: any) => {
          if (mesh.material) {
            mesh.material.wireframe = wireframe;
          }
        });

        if (meshes.length > 0) {
          let minY = Infinity;
          let maxY = -Infinity;
          meshes.forEach((mesh: any) => {
            const boundingInfo = mesh.getBoundingInfo();
            minY = Math.min(minY, boundingInfo.boundingBox.minimumWorld.y);
            maxY = Math.max(maxY, boundingInfo.boundingBox.maximumWorld.y);
          });
          const height = maxY - minY;
          const centerY = (maxY + minY) / 2;
          meshes.forEach((mesh: any) => {
            mesh.position.y -= centerY;
          });

          const camera = scene.activeCamera as InstanceType<typeof ArcRotateCamera>;
          if (camera) {
            camera.radius = height * 2;
            camera.target = Vector3.Zero();
          }
        }
      } catch (error) {
        console.error("Error loading model:", error);
      } finally {
        setLoadingModel(false);
      }
    };

    loadModel();
  }, [modelUrl, webglSupported]);

  useEffect(() => {
    if (!sceneRef.current) return;
    sceneRef.current.meshes.forEach((mesh: any) => {
      if (mesh.material) {
        mesh.material.wireframe = wireframe;
      }
    });
  }, [wireframe]);

  // WebGL not supported fallback
  if (webglSupported === false || initError) {
    return (
      <div className="relative w-full h-full min-h-[400px] rounded-lg overflow-hidden bg-[#14141a] flex items-center justify-center" data-testid="viewer-container">
        <div className="text-center p-8">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
            {initError ? (
              <AlertTriangle className="w-10 h-10 text-amber-500" />
            ) : (
              <Monitor className="w-10 h-10 text-muted-foreground" />
            )}
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {initError ? "3D 뷰어 초기화 실패" : "WebGL이 지원되지 않습니다"}
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            {initError 
              ? initError 
              : "3D 모델을 보려면 WebGL을 지원하는 브라우저가 필요합니다. Chrome, Firefox, 또는 Edge 최신 버전을 사용해 주세요."}
          </p>
          {modelUrl && (
            <a
              href={modelUrl}
              download
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover-elevate"
            >
              모델 다운로드
            </a>
          )}
        </div>
      </div>
    );
  }

  // Still checking WebGL support
  if (webglSupported === null) {
    return (
      <div className="relative w-full h-full min-h-[400px] rounded-lg overflow-hidden bg-[#14141a] flex items-center justify-center" data-testid="viewer-container">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[400px] rounded-lg overflow-hidden bg-[#14141a]" data-testid="viewer-container">
      <canvas
        ref={canvasRef}
        className="w-full h-full touch-none"
        data-testid="babylon-canvas"
      />
      
      {(isLoading || loadingModel) && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
            <span className="text-sm text-muted-foreground">
              {isLoading ? "3D 모델 생성 중..." : "모델 로딩 중..."}
            </span>
          </div>
        </div>
      )}

      {!modelUrl && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
              <svg
                className="w-12 h-12 text-primary/60"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M21 7.5l-2.25-1.313M21 7.5v2.25m0-2.25l-2.25 1.313M3 7.5l2.25-1.313M3 7.5l2.25 1.313M3 7.5v2.25m9 3l2.25-1.313M12 12.75l-2.25-1.313M12 12.75V15m0 6.75l2.25-1.313M12 21.75V19.5m0 2.25l-2.25-1.313m0-16.875L12 2.25l2.25 1.313M21 14.25v2.25l-2.25 1.313m-13.5 0L3 16.5v-2.25"
                />
              </svg>
            </div>
            <p className="text-muted-foreground text-sm">
              프롬프트를 입력하여 3D 캐릭터를 생성하세요
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * WebGL Visualizer - Atmospheric particle effects for Gothic UI.
 * 
 * Creates WebGL-based visual effects including:
 * - Floating fog/mist particles
 * - Ember particles
 * - Dust motes
 * - Rain drops
 * - Lightning flashes
 * 
 * Task 4.3: Implement WebGL Visualizer
 * Validates: Requirements 4.1, 4.2
 */

// Vertex shader for particles
const vertexShaderSource = `
  attribute vec2 a_position;
  attribute float a_size;
  attribute float a_alpha;
  
  uniform vec2 u_resolution;
  
  varying float v_alpha;
  
  void main() {
    vec2 clipSpace = (a_position / u_resolution) * 2.0 - 1.0;
    gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);
    gl_PointSize = a_size;
    v_alpha = a_alpha;
  }
`;

// Fragment shader for particles
const fragmentShaderSource = `
  precision mediump float;
  
  uniform vec4 u_color;
  varying float v_alpha;
  
  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) {
      discard;
    }
    float alpha = v_alpha * (1.0 - dist * 2.0);
    gl_FragColor = vec4(u_color.rgb, u_color.a * alpha);
  }
`;

/**
 * Particle configuration
 */
interface ParticleConfig {
  count: number;
  color: [number, number, number, number];
  minSize: number;
  maxSize: number;
  minSpeed: number;
  maxSpeed: number;
  minAlpha: number;
  maxAlpha: number;
  drift: { x: number; y: number };
}

/**
 * Individual particle
 */
interface Particle {
  x: number;
  y: number;
  size: number;
  alpha: number;
  speed: number;
  angle: number;
  drift: { x: number; y: number };
  life: number;
  maxLife: number;
}

/**
 * WebGL Visualizer for atmospheric effects
 */
export class WebGLVisualizer {
  private canvas: HTMLCanvasElement;
  private gl: WebGLRenderingContext | null;
  private program: WebGLProgram | null = null;
  private particles: Particle[] = [];
  private animationId: number | null = null;
  private config: ParticleConfig;
  private buffers: {
    position: WebGLBuffer | null;
    size: WebGLBuffer | null;
    alpha: WebGLBuffer | null;
  } = { position: null, size: null, alpha: null };

  // Atmosphere settings
  private fogIntensity: number = 0.8;
  private emberIntensity: number = 0.3;
  private lightningActive: boolean = false;

  constructor(canvas: HTMLCanvasElement, config?: Partial<ParticleConfig>) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl', {
      alpha: true,
      premultipliedAlpha: false,
      antialias: true,
    });

    // Default particle configuration for fog
    this.config = {
      count: 200,
      color: [0.5, 0.5, 0.6, 0.3],
      minSize: 2,
      maxSize: 8,
      minSpeed: 0.1,
      maxSpeed: 0.5,
      minAlpha: 0.1,
      maxAlpha: 0.4,
      drift: { x: 0.2, y: -0.1 },
      ...config,
    };

    this.init();
  }

  /**
   * Initialize WebGL context and shaders
   */
  private init(): void {
    if (!this.gl) {
      console.warn('WebGL not supported');
      return;
    }

    const gl = this.gl;

    // Create shaders
    const vertexShader = this.createShader(gl.VERTEX_SHADER, vertexShaderSource);
    const fragmentShader = this.createShader(gl.FRAGMENT_SHADER, fragmentShaderSource);

    if (!vertexShader || !fragmentShader) {
      console.error('Failed to create shaders');
      return;
    }

    // Create program
    this.program = gl.createProgram();
    gl.attachShader(this.program, vertexShader);
    gl.attachShader(this.program, fragmentShader);
    gl.linkProgram(this.program);

    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(this.program));
      return;
    }

    // Create buffers
    this.buffers.position = gl.createBuffer();
    this.buffers.size = gl.createBuffer();
    this.buffers.alpha = gl.createBuffer();

    // Initialize particles
    this.initParticles();

    // Handle resize
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  /**
   * Create a WebGL shader
   */
  private createShader(type: number, source: string): WebGLShader | null {
    if (!this.gl) return null;

    const shader = this.gl.createShader(type);
    if (!shader) return null;

    this.gl.shaderSource(shader, source);
    this.gl.compileShader(shader);

    if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
      console.error('Shader compile error:', this.gl.getShaderInfoLog(shader));
      this.gl.deleteShader(shader);
      return null;
    }

    return shader;
  }

  /**
   * Initialize particles
   */
  private initParticles(): void {
    this.particles = [];

    for (let i = 0; i < this.config.count; i++) {
      this.particles.push(this.createParticle());
    }
  }

  /**
   * Create a single particle
   */
  private createParticle(): Particle {
    return {
      x: Math.random() * this.canvas.width,
      y: Math.random() * this.canvas.height,
      size: this.config.minSize + Math.random() * (this.config.maxSize - this.config.minSize),
      alpha: this.config.minAlpha + Math.random() * (this.config.maxAlpha - this.config.minAlpha),
      speed: this.config.minSpeed + Math.random() * (this.config.maxSpeed - this.config.minSpeed),
      angle: Math.random() * Math.PI * 2,
      drift: {
        x: (Math.random() - 0.5) * this.config.drift.x,
        y: (Math.random() - 0.5) * this.config.drift.y,
      },
      life: Math.random() * 1000,
      maxLife: 500 + Math.random() * 1000,
    };
  }

  /**
   * Resize canvas to fill screen
   */
  resize(): void {
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = window.innerWidth * dpr;
    this.canvas.height = window.innerHeight * dpr;
    this.canvas.style.width = `${window.innerWidth}px`;
    this.canvas.style.height = `${window.innerHeight}px`;

    if (this.gl) {
      this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    }
  }

  /**
   * Start the visualization
   */
  start(): void {
    if (this.animationId !== null) return;

    const animate = () => {
      this.update();
      this.render();
      this.animationId = requestAnimationFrame(animate);
    };

    animate();
  }

  /**
   * Stop the visualization
   */
  stop(): void {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  /**
   * Update particle positions
   */
  private update(): void {
    const width = this.canvas.width;
    const height = this.canvas.height;

    for (const particle of this.particles) {
      // Update position based on drift and speed
      particle.x += particle.drift.x * particle.speed;
      particle.y += particle.drift.y * particle.speed;

      // Add some randomness to movement
      particle.x += Math.sin(particle.life * 0.01) * 0.3;
      particle.y += Math.cos(particle.life * 0.01) * 0.2;

      // Update life
      particle.life += particle.speed;

      // Fade in/out based on life
      const lifeRatio = particle.life / particle.maxLife;
      if (lifeRatio < 0.2) {
        particle.alpha = (lifeRatio / 0.2) * this.config.maxAlpha;
      } else if (lifeRatio > 0.8) {
        particle.alpha = ((1 - lifeRatio) / 0.2) * this.config.maxAlpha;
      }

      // Reset particle if it goes off screen or dies
      if (
        particle.x < -50 ||
        particle.x > width + 50 ||
        particle.y < -50 ||
        particle.y > height + 50 ||
        particle.life >= particle.maxLife
      ) {
        Object.assign(particle, this.createParticle());
        // Respawn from edges
        if (particle.drift.x > 0) {
          particle.x = -10;
        } else if (particle.drift.x < 0) {
          particle.x = width + 10;
        }
        if (particle.drift.y > 0) {
          particle.y = -10;
        } else if (particle.drift.y < 0) {
          particle.y = height + 10;
        }
      }
    }
  }

  /**
   * Render particles to canvas
   */
  private render(): void {
    if (!this.gl || !this.program) return;

    const gl = this.gl;

    // Clear canvas
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    // Enable blending
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    // Use program
    gl.useProgram(this.program);

    // Get attribute locations
    const positionLoc = gl.getAttribLocation(this.program, 'a_position');
    const sizeLoc = gl.getAttribLocation(this.program, 'a_size');
    const alphaLoc = gl.getAttribLocation(this.program, 'a_alpha');

    // Get uniform locations
    const resolutionLoc = gl.getUniformLocation(this.program, 'u_resolution');
    const colorLoc = gl.getUniformLocation(this.program, 'u_color');

    // Set uniforms
    gl.uniform2f(resolutionLoc, this.canvas.width, this.canvas.height);

    // Adjust color for lightning
    let color = [...this.config.color];
    if (this.lightningActive) {
      color = [1, 1, 1, 0.8]; // White flash
    }

    gl.uniform4fv(colorLoc, color);

    // Prepare data arrays
    const positions: number[] = [];
    const sizes: number[] = [];
    const alphas: number[] = [];

    for (const particle of this.particles) {
      positions.push(particle.x, particle.y);
      sizes.push(particle.size * (this.lightningActive ? 2 : 1));
      alphas.push(particle.alpha * this.fogIntensity);
    }

    // Upload position data
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.position);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(positionLoc);
    gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

    // Upload size data
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.size);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(sizes), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(sizeLoc);
    gl.vertexAttribPointer(sizeLoc, 1, gl.FLOAT, false, 0, 0);

    // Upload alpha data
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.alpha);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(alphas), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(alphaLoc);
    gl.vertexAttribPointer(alphaLoc, 1, gl.FLOAT, false, 0, 0);

    // Draw particles
    gl.drawArrays(gl.POINTS, 0, this.particles.length);
  }

  /**
   * Set fog intensity
   */
  setFogIntensity(intensity: number): void {
    this.fogIntensity = Math.max(0, Math.min(1, intensity));
  }

  /**
   * Set ember intensity
   */
  setEmberIntensity(intensity: number): void {
    this.emberIntensity = Math.max(0, Math.min(1, intensity));
  }

  /**
   * Trigger a lightning flash
   */
  triggerLightning(): void {
    this.lightningActive = true;
    setTimeout(() => {
      this.lightningActive = false;
    }, 150);

    // Secondary flash
    setTimeout(() => {
      this.lightningActive = true;
      setTimeout(() => {
        this.lightningActive = false;
      }, 100);
    }, 200);
  }

  /**
   * Change atmosphere preset
   */
  setAtmosphere(preset: 'fog' | 'rain' | 'embers' | 'dust' | 'mist'): void {
    const presets: Record<string, Partial<ParticleConfig>> = {
      fog: {
        color: [0.5, 0.5, 0.6, 0.3],
        minSize: 3,
        maxSize: 10,
        drift: { x: 0.2, y: -0.05 },
      },
      rain: {
        color: [0.6, 0.7, 0.8, 0.2],
        minSize: 1,
        maxSize: 3,
        minSpeed: 3,
        maxSpeed: 8,
        drift: { x: 0.1, y: 5 },
      },
      embers: {
        color: [1, 0.4, 0.1, 0.6],
        minSize: 2,
        maxSize: 5,
        drift: { x: 0.3, y: -1 },
      },
      dust: {
        color: [0.8, 0.7, 0.6, 0.15],
        minSize: 1,
        maxSize: 3,
        drift: { x: 0.1, y: 0.05 },
      },
      mist: {
        color: [0.6, 0.65, 0.7, 0.2],
        minSize: 4,
        maxSize: 12,
        drift: { x: 0.05, y: 0 },
      },
    };

    Object.assign(this.config, presets[preset]);
    this.initParticles();
  }

  /**
   * Clean up WebGL resources
   */
  destroy(): void {
    this.stop();

    if (this.gl) {
      if (this.program) {
        this.gl.deleteProgram(this.program);
      }
      if (this.buffers.position) {
        this.gl.deleteBuffer(this.buffers.position);
      }
      if (this.buffers.size) {
        this.gl.deleteBuffer(this.buffers.size);
      }
      if (this.buffers.alpha) {
        this.gl.deleteBuffer(this.buffers.alpha);
      }
    }
  }
}

/**
 * Create and initialize the visualizer
 */
export function createVisualizer(canvasId: string): WebGLVisualizer | null {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
  if (!canvas) {
    console.error(`Canvas element "${canvasId}" not found`);
    return null;
  }

  const visualizer = new WebGLVisualizer(canvas);
  visualizer.start();

  return visualizer;
}

// Auto-initialize if canvas exists
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('gothic-canvas') as HTMLCanvasElement;
    if (canvas) {
      const visualizer = new WebGLVisualizer(canvas);
      visualizer.start();

      // Expose to global for control
      (window as any).gothicVisualizer = visualizer;
    }
  });
}

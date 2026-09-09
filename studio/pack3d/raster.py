"""Rasterizzatore software (numpy) per un parallelepipedo texturizzato."""
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def Rx(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])


def Ry(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])


def Rz(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]])


class Camera:
    def __init__(self, yaw, pitch, roll, scale, tx, ty, dist, cx, cy):
        self.R = Rz(roll) @ Rx(pitch) @ Ry(yaw)
        self.t = np.array([tx, ty, -dist])
        self.f = scale * dist
        self.cx, self.cy = cx, cy

    def project(self, P):
        q = np.asarray(P, float) @ self.R.T + self.t
        z = -q[:, 2]
        return np.stack([self.cx + self.f * q[:, 0] / z, self.cy - self.f * q[:, 1] / z], 1)

    def view(self, P):
        return np.asarray(P, float) @ self.R.T + self.t


def homography(src, dst):
    """src,dst: 4x2. Restituisce H tale che dst ~ H @ [src,1]."""
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, Vt = np.linalg.svd(np.array(A, float))
    return Vt[-1].reshape(3, 3)


def render(faces, cam, size, bg=(255, 255, 255), ss=2, shade=None):
    """faces: lista di dict(name, quad(4x3 obj), tex(np uint8 HxWx3)).
    L'ordine dei vertici del quad corrisponde a tex (0,0),(w,0),(w,h),(0,h)."""
    Wp = Hp = size * ss
    cam2 = Camera.__new__(Camera)
    cam2.R, cam2.t, cam2.f = cam.R, cam.t, cam.f * ss
    cam2.cx, cam2.cy = cam.cx * ss, cam.cy * ss

    out = np.zeros((Hp, Wp, 3), np.float32)
    out[:] = np.array(bg, np.float32)
    alpha = np.zeros((Hp, Wp), np.float32)
    ids = np.zeros((Hp, Wp), np.uint8)

    for fidx, fc in enumerate(faces, start=1):
        quad = np.asarray(fc["quad"], float)
        # backface culling: normale verso la camera?
        n = np.cross(quad[1] - quad[0], quad[3] - quad[0])
        n = n / np.linalg.norm(n)
        centre_v = cam2.view(quad.mean(0, keepdims=True))[0]
        n_v = cam2.R @ n
        if np.dot(n_v, centre_v) < 0:
            continue  # rivolta dall'altra parte

        uv = cam2.project(quad)
        th, tw = fc["tex"].shape[:2]
        src = np.array([[0, 0], [tw, 0], [tw, th], [0, th]], float)
        H = homography(uv, src)  # immagine -> texture

        x0 = max(int(np.floor(uv[:, 0].min())) - 1, 0)
        x1 = min(int(np.ceil(uv[:, 0].max())) + 1, Wp)
        y0 = max(int(np.floor(uv[:, 1].min())) - 1, 0)
        y1 = min(int(np.ceil(uv[:, 1].max())) + 1, Hp)
        if x1 <= x0 or y1 <= y0:
            continue

        yy, xx = np.mgrid[y0:y1, x0:x1]
        px = xx + 0.5
        py = yy + 0.5
        den = H[2, 0] * px + H[2, 1] * py + H[2, 2]
        u = (H[0, 0] * px + H[0, 1] * py + H[0, 2]) / den
        v = (H[1, 0] * px + H[1, 1] * py + H[1, 2]) / den
        inside = (u >= 0) & (u < tw) & (v >= 0) & (v < th) & (den != 0)
        ui = np.clip(u.astype(np.int32), 0, tw - 1)
        vi = np.clip(v.astype(np.int32), 0, th - 1)
        col = fc["tex"][vi, ui].astype(np.float32)
        k = fc.get("shade", 1.0)
        col = np.clip(col * k, 0, 255)
        m = inside
        region = out[y0:y1, x0:x1]
        region[m] = col[m]
        out[y0:y1, x0:x1] = region
        alpha[y0:y1, x0:x1][m] = 1.0
        ids[y0:y1, x0:x1][m] = fidx

    img = Image.fromarray(out.astype(np.uint8)).resize((size, size), Image.LANCZOS)
    a = Image.fromarray((alpha * 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)
    idm = Image.fromarray(ids).resize((size, size), Image.NEAREST)
    return img, a, idm


# --------------------------------------------------------------------------- #
# rasterizzatore a triangoli con z-buffer (superfici curve)
# --------------------------------------------------------------------------- #
def _vertex_normals(V, tris):
    N = np.zeros_like(V)
    a, b, c = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    for k in range(3):
        np.add.at(N, tris[:, k], fn)
    n = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.where(n == 0, 1, n)


def render_mesh(meshes, cam, size, ss=2, bg=(255, 255, 255),
                light=(-0.35, 0.62, 0.70), ambient=0.60, diffuse=0.42,
                spec=0.16, shininess=26.0):
    """Rende una o piu' mesh texturizzate. Ogni mesh e' un dict con
    verts (Nx3), uvs (Nx2), tris (Mx3), tex (HxWx3) e opzionale shade."""
    Wp = Hp = size * ss
    cam2 = Camera.__new__(Camera)
    cam2.R, cam2.t, cam2.f = cam.R, cam.t, cam.f * ss
    cam2.cx, cam2.cy = cam.cx * ss, cam.cy * ss

    col = np.zeros((Hp, Wp, 3), np.float32)
    col[:] = np.array(bg, np.float32)
    zbuf = np.full((Hp, Wp), np.inf, np.float32)
    alpha = np.zeros((Hp, Wp), np.float32)

    L = np.array(light, float)
    L = L / np.linalg.norm(L)
    view = np.array([0.0, 0.0, 1.0])

    for mesh in meshes:
        V, UV, tris = mesh["verts"], mesh["uvs"], mesh["tris"]
        tex = mesh["tex"]
        th, tw = tex.shape[:2]
        N = mesh.get("normals")
        if N is None:
            N = _vertex_normals(V, tris)
        shade = mesh.get("shade", 1.0)

        q = V @ cam2.R.T + cam2.t
        depth = -q[:, 2]
        scr = np.stack([cam2.cx + cam2.f * q[:, 0] / depth,
                        cam2.cy - cam2.f * q[:, 1] / depth], 1)
        Nv = N @ cam2.R.T
        inv = 1.0 / depth

        # illuminazione per vertice (Gouraud): sufficiente su mesh fitte
        nl = np.clip(Nv @ L, 0, 1)
        h = L + view
        h /= np.linalg.norm(h)
        sp = np.clip(Nv @ h, 0, 1) ** shininess
        lit = (ambient + diffuse * nl + spec * sp) * shade

        for t in tris:
            i0, i1, i2 = t
            if depth[i0] <= 0 or depth[i1] <= 0 or depth[i2] <= 0:
                continue
            p0, p1, p2 = scr[i0], scr[i1], scr[i2]
            area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])
            if abs(area) < 1e-9:
                continue
            x0 = max(int(np.floor(min(p0[0], p1[0], p2[0]))), 0)
            x1 = min(int(np.ceil(max(p0[0], p1[0], p2[0]))) + 1, Wp)
            y0 = max(int(np.floor(min(p0[1], p1[1], p2[1]))), 0)
            y1 = min(int(np.ceil(max(p0[1], p1[1], p2[1]))) + 1, Hp)
            if x1 <= x0 or y1 <= y0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1]
            px = xx + 0.5
            py = yy + 0.5
            w0 = ((p1[0] - px) * (p2[1] - py) - (p2[0] - px) * (p1[1] - py)) / area
            w1 = ((p2[0] - px) * (p0[1] - py) - (p0[0] - px) * (p2[1] - py)) / area
            w2 = 1.0 - w0 - w1
            m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not m.any():
                continue
            iw = w0 * inv[i0] + w1 * inv[i1] + w2 * inv[i2]
            z = 1.0 / iw
            sub = zbuf[y0:y1, x0:x1]
            m &= z < sub
            if not m.any():
                continue
            uu = (w0 * UV[i0, 0] * inv[i0] + w1 * UV[i1, 0] * inv[i1]
                  + w2 * UV[i2, 0] * inv[i2]) * z
            vv = (w0 * UV[i0, 1] * inv[i0] + w1 * UV[i1, 1] * inv[i1]
                  + w2 * UV[i2, 1] * inv[i2]) * z
            ui = np.clip((uu * tw).astype(np.int32), 0, tw - 1)
            vi = np.clip((vv * th).astype(np.int32), 0, th - 1)
            sh = (w0 * lit[i0] + w1 * lit[i1] + w2 * lit[i2])[..., None]
            c = np.clip(tex[vi, ui].astype(np.float32) * sh, 0, 255)
            reg = col[y0:y1, x0:x1]
            reg[m] = c[m]
            col[y0:y1, x0:x1] = reg
            sub[m] = z[m]
            zbuf[y0:y1, x0:x1] = sub
            alpha[y0:y1, x0:x1][m] = 1.0

    img = Image.fromarray(col.astype(np.uint8)).resize((size, size), Image.LANCZOS)
    a = Image.fromarray((alpha * 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)
    return img, a

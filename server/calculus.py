import math


# https://stackoverflow.com/questions/6048975/google-maps-v3-how-to-calculate-the-zoom-level-for-a-given-bounds
def get_bounds_zoom_level(bounds, map_dim):
    WORLD_DIM = {"height": 256, "width": 256}
    ZOOM_MAX = 21

    def lat_rad(lat):
        sin = math.sin(lat * math.pi / 180)
        rad_x2 = math.log((1 + sin) / (1 - sin)) / 2
        return max(min(rad_x2, math.pi), -math.pi) / 2

    def zoom(map_px, world_px, fraction):
        return math.floor(math.log(map_px / world_px / fraction) / math.log(2))

    ne = bounds["NorthEast"]
    sw = bounds["SouthWest"]

    lat_fraction = (lat_rad(ne["Latitude"]) - lat_rad(sw["Latitude"])) / math.pi

    lng_diff = ne["Longitude"] - sw["Longitude"]
    lng_fraction = (lng_diff + 360) % 360 / 360

    lat_zoom = zoom(map_dim["height"], WORLD_DIM["height"], lat_fraction)
    lng_zoom = zoom(map_dim["width"], WORLD_DIM["width"], lng_fraction)

    return min(lat_zoom, lng_zoom, ZOOM_MAX)

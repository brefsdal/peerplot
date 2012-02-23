function frame_header() {
    ax_bb[0] = [80.0,257.454545455,80.0,432.0,576.0,257.454545455,576.0,432.0];
    ax_bb[1] = [80.0,48.0,80.0,222.545454545,576.0,48.0,576.0,222.545454545];
    frame_body_c();
}

function frame_body_c() {
    resize_canvas(id,640,480);
    native_w[id] = 640;
    native_h[id] = 480;

    c.width=640;
    c.height=480;
    c.textBaseline='alphabetic';
    c.fillStyle='rgba(191, 191, 191, 1)';
    c.strokeStyle='rgba(255, 255, 255, 1)';
}

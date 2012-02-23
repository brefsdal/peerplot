function frame_header() { 
    
    var im_left_to_load_c = 1;
    var canvas_image_636f0404dffe11e0b4df00241dd92d62 = 'data:image/png;base64,iVB==';

    function imageLoaded_636f0404dffe11e0b4df00241dd92d62(ev) {
        im = ev.target;
        im_left_to_load_c -=1;
        if (im_left_to_load_c == 0)
            frame_body_c();
    }

    canv_im_636f0404dffe11e0b4df00241dd92d62 = new Image();
    canv_im_636f0404dffe11e0b4df00241dd92d62.onload = imageLoaded_636f0404dffe11e0b4df00241dd92d62;
    canv_im_636f0404dffe11e0b4df00241dd92d62.src = canvas_image_636f0404dffe11e0b4df00241dd92d62;

    ax_bb[0] = [136.0,48.0,136.0,432.0,520.0,48.0,520.0,432.0];
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
    c.lineCap='square';
    c.lineWidth=1.11;
    c.beginPath();
    c.moveTo(0.50,480.50);
    c.lineTo(640.50,480.50);
    c.lineTo(640.50,0.50);
    c.lineTo(0.50,0.50);
    c.lineTo(0.50,480.50);
    c.stroke();
    c.fill();
    c.fillStyle='#000000';
    c.drawImage(canv_im_636f0404dffe11e0b4df00241dd92d62, 136, 48, 385, 385);
    c.strokeStyle='rgba(0, 0, 0, 1)'; 
}

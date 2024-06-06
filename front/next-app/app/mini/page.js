"use client";
import dynamic from 'next/dynamic';

import { useEffect, useState } from "react";

const MapWithNoSSR = dynamic(() => import('./../../components/MapComponent'), {
  ssr: false
});
export default function Home({ tg_id }) {
  const [markers, setMarkers] = useState([]);

  useEffect(() => {
    const fetchMarkers = async () => {
      console.log(process.env.NEXT_PUBLIC_BACK_URL)
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_BACK_URL}/api/userObj`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({"tg_id" : tg_id })
        });
        const data = await res.json();
        if (data.userObj && data.userObj.markers) {
          setMarkers(data.userObj.markers);
        } else {
          setMarkers([
            {"position": [41.695894, 44.801478], "popup": "Wyndham Grand front"}
          ]);
        }
      } catch (error) {
        console.error("Error fetching markers:", error);
        setMarkers([
          {"position": [41.695894, 44.801478], "popup": "Wyndham Grand front"}
        ]);
      }
    };

    fetchMarkers();
  }, [tg_id]);

  return (
    <div>
      <h1>карта марадеров</h1>
      <MapWithNoSSR markers={markers} />
    </div>
  );
}

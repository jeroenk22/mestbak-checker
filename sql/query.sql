-- mestbak-checker query
-- Haalt klanten op die gepland staan voor een opgegeven datum.
-- Alleen vaste herhalende klanten (SjOrderId IS NOT NULL).
-- 
-- Gebruik: pas @Datum aan naar de gewenste datum (formaat: YYYY-MM-DD)
-- In het Python script wordt @Datum automatisch ingevuld als morgen.

DECLARE @Datum DATE;
SET @Datum = '2026-04-07'; -- Aanpassen voor handmatig testen

DECLARE @ClientNo INT;
SET @ClientNo = 3582; -- Aanpassen voor andere klant

SELECT 
    os.OrderId,
    o.SjOrderId,
    os.LocName,
    os.LocStreet,
    os.LocZip,
    os.LocCity,
    os.LocCountry,
    os.LocPhone,
    os.LocMobile,
    os.MomentRTA
FROM [<db-naam>].[dbo].[ordsubtask] os
JOIN [<db-naam>].[dbo].[orders] o ON os.OrderId = o.OrderId
JOIN [<db-naam>].[dbo].[clients] c ON o.ClientNo = c.ClientNo
LEFT JOIN [<db-naam>].[dbo].[rides] r ON os.RideId = r.RideId
WHERE os.MomentRTA >= @Datum 
  AND os.MomentRTA < DATEADD(DAY, 1, @Datum)
  AND c.ClientNo = @ClientNo
  AND o.deleted <> 1
  AND o.SjOrderId IS NOT NULL
  AND o.SjOrderId <> 0
ORDER BY o.OrderID;

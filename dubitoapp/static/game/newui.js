$(document).ready(function () {
    $("#my_cards").sortable()
    $("#stacked_card").flip()
    $('[data-toggle="popover"]').popover({
        html: true,
        animation: false,
        trigger: 'manual',
        template: '<div class="popover shadow-md" role="tooltip"><div class="arrow"></div><div class="popover-body exclamation-point"></div>',
    })
    $('[data-toggle="popover"]').on('shown.bs.popover', function () {
        var $pop = $(this);
        setTimeout(function () {
            $pop.popover('hide');
        }, 4500);
    });
})
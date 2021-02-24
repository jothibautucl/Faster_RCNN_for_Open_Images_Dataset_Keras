from libraries import *


def train_rpn(num_epochs, epoch_length, r_epochs, total_epochs, best_loss):
    start_time = time.time()
    print("Rpn training:")

    for epoch_num in range(num_epochs):

        data_gen_train = get_anchor_gt(train_imgs, C, get_img_output_length, mode='train')

        iter_num = 0
        progbar = generic_utils.Progbar(epoch_length)
        print('Epoch {}/{}'.format(r_epochs + 1, total_epochs))

        r_epochs += 1

        while True:
            try:

                # Generate X (x_img) and label Y ([y_rpn_cls, y_rpn_regr])
                X, Y, img_data, debug_img, debug_num_pos = next(data_gen_train)

                # Train rpn model and get loss value [_, loss_rpn_cls, loss_rpn_regr]
                loss_rpn = model_rpn.train_on_batch(X, Y)
                losses[iter_num, 0] = loss_rpn[1]
                losses[iter_num, 1] = loss_rpn[2]
                iter_num += 1

                progbar.update(iter_num, [('rpn_cls', np.mean(losses[:iter_num, 0])),
                                          ('rpn_regr', np.mean(losses[:iter_num, 1]))])

                if iter_num == epoch_length:
                    loss_rpn_cls = np.mean(losses[:, 0])
                    loss_rpn_regr = np.mean(losses[:, 1])

                    if C.verbose:
                        # print('Classifier accuracy for bounding boxes from RPN: {}'.format(class_acc))
                        print('Loss RPN classifier: {}'.format(loss_rpn_cls))
                        print('Loss RPN regression: {}'.format(loss_rpn_regr))
                        # print('Loss Detector classifier: {}'.format(loss_class_cls))
                        # print('Loss Detector regression: {}'.format(loss_class_regr))
                        print('Total loss: {}'.format(loss_rpn_cls + loss_rpn_regr))
                        print('Elapsed time: {}'.format(time.time() - start_time))
                        # elapsed_time = (time.time() - start_time) / 60

                    curr_loss = loss_rpn_cls + loss_rpn_regr

                    # loss_rpn_cls_at_epoch[epoch_num] = loss_rpn_cls
                    # loss_rpn_regr_at_epoch[epoch_num] = loss_rpn_regr

                    if curr_loss < best_loss:
                        if C.verbose:
                            print('Total loss decreased from {} to {}, saving weights'.format(best_loss, curr_loss))
                        best_loss = curr_loss
                        model_all.save_weights(C.model_path)

                    break

            except Exception as e:
                print('Exception: {}'.format(e))
                continue
    return best_loss


def train_classifier(num_epochs, epoch_length, r_epochs, total_epochs, best_loss):
    global record_df
    start_time = time.time()
    rpn_accuracy_rpn_monitor = []
    rpn_accuracy_for_epoch = []
    print("Classifier training:")
    for epoch_num in range(num_epochs):

        data_gen_train = get_anchor_gt(train_imgs, C, get_img_output_length, mode='train')

        iter_num = 0
        progbar = generic_utils.Progbar(epoch_length)
        print('Epoch {}/{}'.format(r_epochs + 1, total_epochs))

        r_epochs += 1

        while True:
            try:

                if len(rpn_accuracy_rpn_monitor) == epoch_length and C.verbose:
                    mean_overlapping_bboxes = float(sum(rpn_accuracy_rpn_monitor)) / len(rpn_accuracy_rpn_monitor)
                    rpn_accuracy_rpn_monitor = []
                    # print('Average number of overlapping bounding boxes from RPN = {} for {} previous
                    # iterations'.format(mean_overlapping_bboxes, epoch_length))
                    if mean_overlapping_bboxes == 0:
                        print(
                            'RPN is not producing bounding boxes that overlap the ground truth boxes. Check RPN '
                            'settings or keep training.')

                # Generate X (x_img) and label Y ([y_rpn_cls, y_rpn_regr])
                X, Y, img_data, debug_img, debug_num_pos = next(data_gen_train)

                # Generate inputs for the classifier model from the rpn model
                X2, Y1, Y2, sel_samples = rpn_to_class(X, img_data, rpn_accuracy_rpn_monitor, rpn_accuracy_for_epoch)

                if X2 is None:
                    continue

                # training_data: [X, X2[:, sel_samples, :]]
                # labels: [Y1[:, sel_samples, :], Y2[:, sel_samples, :]]
                #  X                     => img_data resized image
                #  X2[:, sel_samples, :] => num_rois (4 in here) bboxes which contains selected neg and pos
                #  Y1[:, sel_samples, :] => one hot encode for num_rois bboxes which contains selected neg and pos
                #  Y2[:, sel_samples, :] => labels and gt bboxes for num_rois bboxes which contains selected neg and pos
                loss_class = model_classifier.train_on_batch([X, X2[:, sel_samples, :]],
                                                             [Y1[:, sel_samples, :], Y2[:, sel_samples, :]])

                losses[iter_num, 2] = loss_class[1]
                losses[iter_num, 3] = loss_class[2]
                losses[iter_num, 4] = loss_class[3]

                iter_num += 1

                progbar.update(iter_num,
                               [('rpn_cls', np.mean(losses[:iter_num, 0])), ('rpn_regr', np.mean(losses[:iter_num, 1])),
                                ('final_cls', np.mean(losses[:iter_num, 2])),
                                ('final_regr', np.mean(losses[:iter_num, 3]))])

                if iter_num == epoch_length:
                    loss_class_cls = np.mean(losses[:, 2])
                    loss_class_regr = np.mean(losses[:, 3])
                    class_acc = np.mean(losses[:, 4])

                    mean_overlapping_bboxes = float(sum(rpn_accuracy_for_epoch)) / len(rpn_accuracy_for_epoch)
                    rpn_accuracy_for_epoch = []

                    if C.verbose:
                        print('Mean number of bounding boxes from RPN overlapping ground truth boxes: {}'.format(
                            mean_overlapping_bboxes))
                        print('Classifier accuracy for bounding boxes from RPN: {}'.format(class_acc))
                        # print('Loss RPN classifier: {}'.format(loss_rpn_cls))
                        # print('Loss RPN regression: {}'.format(loss_rpn_regr))
                        print('Loss Detector classifier: {}'.format(loss_class_cls))
                        print('Loss Detector regression: {}'.format(loss_class_regr))
                        print('Total loss: {}'.format(loss_class_cls + loss_class_regr))
                        print('Elapsed time: {}'.format(time.time() - start_time))
                        elapsed_time = (time.time() - start_time) / 60

                    curr_loss = loss_class_cls + loss_class_regr
                    iter_num = 0
                    start_time = time.time()

                    if curr_loss < best_loss:
                        if C.verbose:
                            print('Total loss decreased from {} to {}, saving weights'.format(best_loss, curr_loss))
                        best_loss = curr_loss
                        model_all.save_weights(C.model_path)

                    # new_row = {'mean_overlapping_bboxes': round(mean_overlapping_bboxes, 3),
                    #            'class_acc': round(class_acc, 3),
                    #            'loss_rpn_cls': round(loss_rpn_cls_at_epoch[epoch_num], 3),
                    #            'loss_rpn_regr': round(loss_rpn_regr_at_epoch[epoch_num], 3),
                    #            'loss_class_cls': round(loss_class_cls, 3),
                    #            'loss_class_regr': round(loss_class_regr, 3),
                    #            'curr_loss_classifier': round(curr_loss, 3),
                    #            'curr_loss_rpn': round(
                    #                loss_rpn_regr_at_epoch[epoch_num] + loss_rpn_cls_at_epoch[epoch_num], 3),
                    #            'elapsed_time': round(elapsed_time, 3),
                    #            'mAP': 0}
                    #
                    # record_df = record_df.append(new_row, ignore_index=True)
                    # record_df.to_csv(record_path, index=0)

                    break

            except Exception as e:
                print('Exception: {}'.format(e))
                continue
    return best_loss


def rpn_to_class(X, img_data, rpn_accuracy_rpn_monitor, rpn_accuracy_for_epoch):
    # Get predicted rpn from rpn model [rpn_cls, rpn_regr]
    P_rpn = model_rpn.predict_on_batch(X)

    # R: bboxes (shape=(300,4))
    # Convert rpn layer to roi bboxes
    R = rpn_to_roi(P_rpn[0], P_rpn[1], C, K.image_data_format(), use_regr=True, overlap_thresh=0.7,
                   max_boxes=300)

    # note: calc_iou converts from (x1,y1,x2,y2) to (x,y,w,h) format
    # X2: bboxes that iou > C.classifier_min_overlap for all gt bboxes in 300 non_max_suppression bboxes
    # Y1: one hot code for bboxes from above => x_roi (X)
    # Y2: corresponding labels and corresponding gt bboxes
    X2, Y1, Y2, IouS = calc_iou(R, img_data, C, class_mapping)

    # If X2 is None means there are no matching bboxes
    if X2 is None:
        rpn_accuracy_rpn_monitor.append(0)
        rpn_accuracy_for_epoch.append(0)
        return None, None, None, None

    # Find out the positive anchors and negative anchors
    neg_samples = np.where(Y1[0, :, -1] == 1)
    pos_samples = np.where(Y1[0, :, -1] == 0)

    if len(neg_samples) > 0:
        neg_samples = neg_samples[0]
    else:
        neg_samples = []

    if len(pos_samples) > 0:
        pos_samples = pos_samples[0]
    else:
        pos_samples = []

    rpn_accuracy_rpn_monitor.append(len(pos_samples))
    rpn_accuracy_for_epoch.append((len(pos_samples)))

    if C.num_rois > 1:
        # If number of positive anchors is larger than 4//2 = 2, randomly choose 2 pos samples
        if len(pos_samples) < C.num_rois // 2:
            selected_pos_samples = pos_samples.tolist()
        else:
            selected_pos_samples = np.random.choice(pos_samples, C.num_rois // 2, replace=False).tolist()

        # Randomly choose (num_rois - num_pos) neg samples
        try:
            selected_neg_samples = np.random.choice(neg_samples, C.num_rois - len(selected_pos_samples),
                                                    replace=False).tolist()
        except:
            selected_neg_samples = np.random.choice(neg_samples, C.num_rois - len(selected_pos_samples),
                                                    replace=True).tolist()

        # Save all the pos and neg samples in sel_samples
        sel_samples = selected_pos_samples + selected_neg_samples
    else:
        # in the extreme case where num_rois = 1, we pick a random pos or neg sample
        selected_pos_samples = pos_samples.tolist()
        selected_neg_samples = neg_samples.tolist()
        if np.random.randint(0, 2):
            sel_samples = random.choice(neg_samples)
        else:
            sel_samples = random.choice(pos_samples)

    return X2, Y1, Y2, sel_samples


if __name__ == "__main__":
    base_path = '.'

    train_path = './data/valid_data_annotations.txt'  # Training data (annotation file)
    data_path = './data'

    num_rois = 4  # Number of RoIs to process at once.

    # Augmentation flag
    horizontal_flips = True  # Augment with horizontal flips in training.
    vertical_flips = True  # Augment with vertical flips in training.
    rot_90 = True  # Augment with 90 degree rotations in training.

    output_weight_path = os.path.join(base_path, 'model/weights_test2epoch_supervised.hdf5')

    record_path = os.path.join(base_path,
                               'model/record_test2epoch_supervised.csv')  # Record data (used to save the losses, classification accuracy and mean average precision)

    base_weight_path = os.path.join(base_path, 'model/vgg16_weights_tf_dim_ordering_tf_kernels.h5')

    config_output_filename = os.path.join(base_path, 'model_vgg_config.pickle')

    C = Config()

    C.use_horizontal_flips = horizontal_flips
    C.use_vertical_flips = vertical_flips
    C.rot_90 = rot_90

    C.record_path = record_path
    C.model_path = output_weight_path
    C.num_rois = num_rois

    C.base_net_weights = base_weight_path

    st = time.time()
    train_imgs, classes_count, class_mapping = get_data(train_path, data_path)
    print()
    print('Spend %0.2f mins to load the data' % ((time.time() - st) / 60))

    if 'bg' not in classes_count:
        classes_count['bg'] = 0
        class_mapping['bg'] = len(class_mapping)
    # e.g.
    #    classes_count: {'Car': 2383, 'Mobile phone': 1108, 'Person': 3745, 'bg': 0}
    #    class_mapping: {'Person': 0, 'Car': 1, 'Mobile phone': 2, 'bg': 3}
    C.class_mapping = class_mapping

    print('Training images per class:')
    pprint.pprint(classes_count)
    print('Num classes (including bg) = {}'.format(len(classes_count)))
    print(class_mapping)

    # Save the configuration
    with open(config_output_filename, 'wb') as config_f:
        pickle.dump(C, config_f)
        print('Config has been written to {}, and can be loaded when testing to ensure correct results'.format(
            config_output_filename))

    random.seed(1)
    random.shuffle(train_imgs)

    print('Num train samples (images) {}'.format(len(train_imgs)))

    input_shape_img = (None, None, 3)

    img_input = Input(shape=input_shape_img)
    roi_input = Input(shape=(None, 4))

    # define the base network (VGG here, can be Resnet50, Inception, etc)
    shared_layers = nn_base(img_input, trainable=True)

    # define the RPN, built on the base layers
    num_anchors = len(C.anchor_box_scales) * len(C.anchor_box_ratios)  # 9
    rpn = rpn_layer(shared_layers, num_anchors)

    classifier = classifier_layer(shared_layers, roi_input, C.num_rois, nb_classes=len(classes_count))

    model_rpn = Model(img_input, rpn[:2])
    model_classifier = Model([img_input, roi_input], classifier)

    # this is a model that holds both the RPN and the classifier, used to load/save weights for the models
    model_all = Model([img_input, roi_input], rpn[:2] + classifier)

    # weights_path = data_utils.get_file(
    #           'vgg16_weights_tf_dim_ordering_tf_kernels.h5',
    #           WEIGHTS_PATH,
    #           cache_subdir='models',
    #           file_hash='64373286793e3c8b2b4e3219cbf3544b')
    # model_classifier.load_weights(weights_path)
    # model_all.load_weights(weights_path)

    # Because the google colab can only run the session several hours one time (then you need to connect again),
    # we need to save the model and load the model to continue training

    # if not os.path.isfile(C.model_path):
    # If this is the beginning of the training, load the pre-traind base network such as vgg-16
    try:
        print('This is the first time of your training')
        print('loading weights from {}'.format(C.base_net_weights))
        model_rpn.load_weights(C.base_net_weights, by_name=True)
        model_classifier.load_weights(C.base_net_weights, by_name=True)
    except:
        print('Could not load pretrained model weights. Weights can be found in the keras application folder \
            https://github.com/fchollet/keras/tree/master/keras/applications')

    # Create the record.csv file to record losses, acc and mAP
    record_df = pd.DataFrame(
        columns=['mean_overlapping_bboxes', 'class_acc', 'loss_rpn_cls', 'loss_rpn_regr', 'loss_class_cls',
                 'loss_class_regr', 'curr_loss_classifier', 'curr_loss_rpn', 'elapsed_time', 'mAP'])
    # else:
    #     # If this is a continued training, load the trained model from before
    #     print('Continue training based on previous trained model')
    #     print('Loading weights from {}'.format(C.model_path))
    #     model_rpn.load_weights(C.model_path, by_name=True)
    #     model_classifier.load_weights(C.model_path, by_name=True)
    #
    #     # Load the records
    #     record_df = pd.read_csv(record_path)
    #
    #     r_mean_overlapping_bboxes = record_df['mean_overlapping_bboxes']
    #     r_class_acc = record_df['class_acc']
    #     r_loss_rpn_cls = record_df['loss_rpn_cls']
    #     r_loss_rpn_regr = record_df['loss_rpn_regr']
    #     r_loss_class_cls = record_df['loss_class_cls']
    #     r_loss_class_regr = record_df['loss_class_regr']
    #     r_curr_loss_classifier = record_df['curr_loss_classifier']
    #     r_curr_loss_rpn = record_df['curr_loss_rpn']
    #     r_elapsed_time = record_df['elapsed_time']
    #     r_mAP = record_df['mAP']
    #
    #     print('Already train %dK batches' % (len(record_df)))

    optimizer = Adam(lr=1e-5)
    optimizer_classifier = Adam(lr=1e-5)
    model_rpn.compile(optimizer=optimizer, loss=[rpn_loss_cls(num_anchors), rpn_loss_regr(num_anchors)])
    model_classifier.compile(optimizer=optimizer_classifier,
                             loss=[class_loss_cls, class_loss_regr(len(classes_count) - 1)],
                             metrics={'dense_class_{}'.format(len(classes_count)): 'accuracy'})
    model_all.compile(optimizer='sgd', loss='mae')

    # Training setting
    total_epochs = len(record_df)
    r_epochs = len(record_df)

    # epoch_length = 100
    # num_epochs = 10 * 4 * 2
    epoch_length = 10
    num_epochs = 2

    total_epochs += num_epochs

    losses = np.zeros((epoch_length, 5))

    # loss_rpn_cls_at_epoch = np.zeros((r_epochs))
    # loss_rpn_regr_at_epoch = np.zeros((r_epochs))

    # if len(record_df) == 0:
    best_loss_rpn = np.Inf
    # else:
    #     best_loss_rpn = np.min(r_curr_loss_rpn)

    best_loss_rpn = train_rpn(num_epochs, epoch_length, r_epochs, total_epochs, best_loss_rpn)

    # if len(record_df) == 0:
    best_loss_classifier = np.Inf
    # else:
    #     best_loss_classifier = np.min(r_curr_loss_classifier)

    best_loss_classifier = train_classifier(num_epochs, epoch_length, r_epochs, total_epochs, best_loss_classifier)

    print('Training complete, exiting.')

    # plt.figure(figsize=(15, 5))
    # plt.subplot(1, 2, 1)
    # plt.plot(np.arange(0, r_epochs), record_df['mean_overlapping_bboxes'], 'r')
    # plt.title('mean_overlapping_bboxes')
    # plt.subplot(1, 2, 2)
    # plt.plot(np.arange(0, r_epochs), record_df['class_acc'], 'r')
    # plt.title('class_acc')
    #
    # plt.show()
    #
    # plt.figure(figsize=(15, 5))
    # plt.subplot(1, 2, 1)
    # plt.plot(np.arange(0, r_epochs), record_df['loss_rpn_cls'], 'r')
    # plt.title('loss_rpn_cls')
    # plt.subplot(1, 2, 2)
    # plt.plot(np.arange(0, r_epochs), record_df['loss_rpn_regr'], 'r')
    # plt.title('loss_rpn_regr')
    # plt.show()
    #
    # plt.figure(figsize=(15, 5))
    # plt.subplot(1, 2, 1)
    # plt.plot(np.arange(0, r_epochs), record_df['loss_class_cls'], 'r')
    # plt.title('loss_class_cls')
    # plt.subplot(1, 2, 2)
    # plt.plot(np.arange(0, r_epochs), record_df['loss_class_regr'], 'r')
    # plt.title('loss_class_regr')
    # plt.show()
    #
    # plt.plot(np.arange(0, r_epochs), record_df['curr_loss_classifier'], 'r')
    # plt.title('total_loss_classifier')
    # plt.show()
    #
    # plt.figure(figsize=(15, 5))
    # plt.subplot(1, 2, 1)
    # plt.plot(np.arange(0, r_epochs), record_df['curr_loss_classifier'], 'r')
    # plt.title('total_loss_classifier')
    # plt.subplot(1, 2, 2)
    # plt.plot(np.arange(0, r_epochs), record_df['elapsed_time'], 'r')
    # plt.title('elapsed_time')
    # plt.show()
    #
    # plt.plot(np.arange(0, r_epochs), record_df['curr_loss_rpn'], 'r')
    # plt.title('total_loss_rpn')
    # plt.show()
    #
    # plt.figure(figsize=(15, 5))
    # plt.subplot(1, 2, 1)
    # plt.plot(np.arange(0, r_epochs), record_df['curr_loss_rpn'], 'r')
    # plt.title('total_loss_rpn')
    # plt.subplot(1, 2, 2)
    # plt.plot(np.arange(0, r_epochs), record_df['elapsed_time'], 'r')
    # plt.title('elapsed_time')
    # plt.show()
    #
    # plt.title('loss')
    # plt.plot(np.arange(0, r_epochs), record_df['loss_rpn_cls'], 'b')
    # plt.plot(np.arange(0, r_epochs), record_df['loss_rpn_regr'], 'g')
    # plt.plot(np.arange(0, r_epochs), record_df['loss_class_cls'], 'r')
    # plt.plot(np.arange(0, r_epochs), record_df['loss_class_regr'], 'c')
    # # plt.plot(np.arange(0, r_epochs), record_df['curr_loss'], 'm')
    # plt.show()
